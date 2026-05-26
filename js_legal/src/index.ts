import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";
import { Client } from "@elastic/elasticsearch";
import { loadConfig } from "./config.js";
import winston from "winston";

const config = loadConfig();

const logger = winston.createLogger({
  level: config.log.level.toLowerCase(),
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.simple(),
      stderrLevels: ['info', 'error', 'warn', 'debug'],
    }),
    ...(config.log.file ? [new winston.transports.File({ filename: config.log.file })] : [])
  ],
});

// Configure Elasticsearch client
let esNode: string;
if (config.es.host.includes("://")) {
  esNode = config.es.host;
  // If a port is specified in config but not in the host string, we could append it,
  // but usually if someone provides a full URL in 'host', they expect it to be used as is.
} else {
  const scheme = config.es.scheme || "http";
  const port = config.es.port && config.es.port !== 0 ? `:${config.es.port}` : ":9200";
  esNode = `${scheme}://${config.es.host || "localhost"}${port}`;
}

const esClient = new Client({
  node: esNode || "http://localhost:9200",
  auth: {
    username: config.es.user,
    password: config.es.password,
  },
});

const INDEX_NAME = config.index.name;

class LegalMcpServer {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: "legal-mcp-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    
    // Error handling
    this.server.onerror = (error) => logger.error("[MCP Error]", error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      logger.info('[LegalMCP] === LIST TOOLS REQUEST RECEIVED ===');
      const tools = [
        {
          name: "search_laws",
          description: "日本の法令データベースから、正式な条文や法律を検索します。専門的な法的根拠が必要な場合や、正確な法令名・条文を確認したい場合に使用してください。",
          inputSchema: {
            type: "object",
            properties: {
              query: { type: "string", description: "検索キーワード（例：'憲法', '所得税法', '個人情報保護'）。自然言語での入力も可能です。" },
              era: { type: "string", description: "日本の元号によるフィルタ（例：'昭和', '平成', '令和'）。" },
              law_type: { type: "string", description: "法令の種類によるフィルタ（例：'Act'（法律）, 'CabinetOrder'（政令）, 'MinisterialOrdinance'（省令））。" },
              limit: { type: "number", description: "取得する最大件数（デフォルトは5）。", default: 5 },
            },
            required: ["query"],
          },
        },
        {
          name: "get_law_by_id",
          description: "指定された法令IDに基づいて、法令の全文または詳細な情報を取得します。特定の法律の正確な文言を確認する場合に最適です。",
          inputSchema: {
            type: "object",
            properties: {
              law_id: { type: "string", description: "法令のユニークID（例：'101AC0000000001'）。" },
            },
            required: ["law_id"],
          },
        },
        {
          name: "get_cluster_status",
          description: "法令データベースの稼働状況を確認します。通常、ユーザーへの回答には使用しません。",
          inputSchema: {
            type: "object",
            properties: {},
          },
        },
        {
          name: "get_index_state",
          description: "法令インデックスの統計情報を取得します。通常、ユーザーへの回答には使用しません。",
          inputSchema: {
            type: "object",
            properties: {},
          },
        },
        {
          name: "get_raw_json_by_id",
          description: "指定された法令の未加工のJSONデータを取得します。非常に詳細な構造情報が必要な場合に使用します。",
          inputSchema: {
            type: "object",
            properties: {
              law_id: { type: "string", description: "法令のユニークID。" },
            },
            required: ["law_id"],
          },
        },
      ];
      logger.info('[LegalMCP] Returning tools:', {
        count: tools.length,
        toolNames: tools.map(t => t.name)
      });
      return { tools };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const toolName = request.params.name;
      const args = request.params.arguments;
      
      logger.info('[LegalMCP] === TOOL CALL REQUEST RECEIVED ===', {
        toolName,
        arguments: args,
        timestamp: new Date().toISOString()
      });
      
      const startTime = Date.now();
      
      try {
        let result;
        switch (toolName) {
          case "search_laws":
            result = await this.handleSearchLaws(args);
            break;
          case "get_law_by_id":
            result = await this.handleGetLawById(args);
            break;
          case "get_cluster_status":
            result = await this.handleGetClusterStatus();
            break;
          case "get_index_state":
            result = await this.handleGetIndexState();
            break;
          case "get_raw_json_by_id":
            result = await this.handleGetRawJsonById(args);
            break;
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${toolName}`
            );
        }
        
        const duration = Date.now() - startTime;
        
        logger.info('[LegalMCP] === TOOL CALL COMPLETED ===', {
          toolName,
          duration: `${duration}ms`,
          resultType: typeof result,
          hasContent: !!result?.content,
          timestamp: new Date().toISOString()
        });
        
        // Log result preview
        if (result?.content && Array.isArray(result.content)) {
          const textContent = result.content
            .filter((block: any) => block.type === 'text')
            .map((block: any) => block.text)
            .join('\n');
          
          logger.info('[LegalMCP] Result preview:', {
            toolName,
            contentLength: textContent?.length || 0,
            preview: textContent?.substring(0, 300) + (textContent && textContent.length > 300 ? '...' : '')
          });
        }
        
        return result;
      } catch (error: any) {
        const duration = Date.now() - startTime;
        
        logger.error('[LegalMCP] === TOOL CALL FAILED ===', {
          toolName,
          error: error.message || String(error),
          stack: error.stack,
          duration: `${duration}ms`,
          timestamp: new Date().toISOString()
        });
        
        return {
          content: [
            {
              type: "text",
              text: `Error: ${error.message || String(error)}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  private async handleSearchLaws(args: any) {
    const { query, era, law_type, limit = 5 } = args;
    logger.info(`Searching for: '${query}' (Era: ${era}, Type: ${law_type}, Limit: ${limit})`);

    const searchBody: any = {
      query: {
        bool: {
          must: [
            {
              multi_match: {
                query: query,
                fields: [
                  "meta.LawTitle_Kanji^3",
                  "meta.LawTitle_Kana",
                  "meta.LawTitle_Abbrev^2",
                  "meta.LawNum",
                  "legal_content.sentence",
                  "legal_content.article_title",
                  "legal_content.article_caption",
                  "legal_content.enact_statement",
                  "legal_content.appdx_table_title",
                  "legal_content.fig_struct_title",
                ],
                type: "best_fields",
              },
            },
          ],
          filter: [],
        },
      },
      highlight: {
        fields: {
          "legal_content.sentence": {
            fragment_size: 200,
            number_of_fragments: 1,
            no_match_size: 200,
          },
          "legal_content.article_title": {
            fragment_size: 150,
            number_of_fragments: 1,
            no_match_size: 150,
          },
          "legal_content.article_caption": {
            fragment_size: 150,
            number_of_fragments: 1,
            no_match_size: 150,
          },
        },
        pre_tags: ["<em>"],
        post_tags: ["</em>"],
        encoder: "html",
      },
    };

    if (era) {
      searchBody.query.bool.filter.push({ term: { "meta.Era": era } });
    }
    if (law_type) {
      searchBody.query.bool.filter.push({ term: { "meta.LawType": law_type } });
    }

    const response = await esClient.search({
      index: INDEX_NAME,
      body: searchBody,
      size: limit,
    });

    const hits = response.hits.hits;
    if (hits.length === 0) {
      return {
        content: [{ type: "text", text: "一致する法令が見つかりませんでした。" }],
      };
    }

    const results = hits.map((hit: any) => {
      const source = hit._source;
      const meta = source.meta || {};
      const title = meta.LawTitle_Kanji || "名称不明";
      const lawNum = meta.LawNum || "番号不明";
      const lawId = source.law_id;
      const highlight = hit.highlight || {};

      let snippet = "";
      for (const field of ["legal_content.sentence", "legal_content.article_title", "legal_content.article_caption"]) {
        if (highlight[field]) {
          snippet = highlight[field][0].replace(/<em>/g, "").replace(/<\/em>/g, "");
          break;
        }
      }

      if (!snippet) {
        const content = source.legal_content || {};
        const sentence = content.sentence || "";
        snippet = sentence ? (sentence.substring(0, 200) + "...") : "内容なし";
      }

      return `ID: ${lawId}\nタイトル: ${title}\n法令番号: ${lawNum}\n内容抜粋: ${snippet}\n---`;
    });

    return {
      content: [{ type: "text", text: results.join("\n\n") }],
    };
  }

  private async handleGetLawById(args: any) {
    const { law_id } = args;
    logger.info(`Retrieving law: ${law_id}`);

    const response: any = await esClient.get({
      index: INDEX_NAME,
      id: law_id,
    });

    const source = response._source;
    const meta = source.meta || {};
    const content = source.legal_content || {};

    const output = [
      `# ${meta.LawTitle_Kanji || "名称不明"}`,
      `ID: ${law_id}`,
      `法令番号: ${meta.LawNum}`,
      `種別: ${meta.LawType}`,
      `制定時期: ${meta.Era} ${meta.Year}`,
      "\n## 法令内容\n",
    ];

    for (const field of ["article_title", "article_caption", "sentence", "enact_statement"]) {
      if (content[field]) {
        const labels: { [key: string]: string } = {
          article_title: "条文タイトル",
          article_caption: "条文見出し",
          sentence: "本文",
          enact_statement: "制定文"
        };
        output.push(`### ${labels[field] || field}`);
        output.push(content[field]);
        output.push("");
      }
    }

    const raw = source.raw_full_json || {};
    if (raw.omitted) {
      output.push("\n*注: このドキュメントの完全なRaw JSON構造は、サイズ制限のため省略されました。*");
    }

    return {
      content: [{ type: "text", text: output.join("\n") }],
    };
  }

  private async handleGetClusterStatus() {
    logger.info("Checking cluster status");
    const health = await esClient.cluster.health();
    const countResponse = await esClient.count({ index: INDEX_NAME });

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            status: health.status,
            nodes: health.number_of_nodes,
            document_count: countResponse.count,
            index_name: INDEX_NAME,
          }, null, 2),
        },
      ],
    };
  }

  private async handleGetIndexState() {
    logger.info("Querying index state");
    try {
      const exists = await esClient.indices.exists({ index: INDEX_NAME });
      if (!exists) {
        return {
          content: [{ type: "text", text: `Index '${INDEX_NAME}' does not exist.` }],
          isError: true
        };
      }

      const statsResponse: any = await esClient.indices.stats({ index: INDEX_NAME });
      const stats = statsResponse.indices[INDEX_NAME].total;
      
      const settingsResponse: any = await esClient.indices.getSettings({ index: INDEX_NAME });
      const settings = settingsResponse[INDEX_NAME].settings.index;

      const state = {
        index_name: INDEX_NAME,
        documents: stats.docs.count,
        store_size_bytes: stats.store.size_in_bytes,
        shards: settings.number_of_shards,
        replicas: settings.number_of_replicas
      };

      return {
        content: [{ type: "text", text: JSON.stringify(state, null, 2) }]
      };
    } catch (error: any) {
      logger.error("Failed to get index state:", error);
      return {
        content: [{ type: "text", text: `Error: ${error.message}` }],
        isError: true
      };
    }
  }

  private async logIndexState() {
    try {
      logger.info(`Connecting to Elasticsearch at ${esNode}`);
      
      const exists = await esClient.indices.exists({ index: INDEX_NAME });
      if (exists) {
        const statsResponse: any = await esClient.indices.stats({ index: INDEX_NAME });
        const stats = statsResponse.indices[INDEX_NAME].total;
        
        logger.info(
          `Elasticsearch index '${INDEX_NAME}' state: ` +
          `documents=${stats.docs.count}, ` +
          `store_size=${stats.store.size_in_bytes} bytes`
        );

        const settingsResponse: any = await esClient.indices.getSettings({ index: INDEX_NAME });
        const settings = settingsResponse[INDEX_NAME].settings.index;
        
        logger.info(
          `Index settings: shards=${settings.number_of_shards}, replicas=${settings.number_of_replicas}`
        );
      } else {
        logger.warn(`Index '${INDEX_NAME}' does not exist`);
      }
      logger.info("Elasticsearch client created successfully");
    } catch (error: any) {
      logger.error(`Failed to get Elasticsearch index state: ${error.message}`);
    }
  }

  private async handleGetRawJsonById(args: any) {
    const { law_id } = args;
    logger.info(`Retrieving raw JSON for law: ${law_id}`);

    const response: any = await esClient.get({
      index: INDEX_NAME,
      id: law_id,
    });

    const source = response._source;
    const raw_full_json = source.raw_full_json || {};

    if (!raw_full_json || Object.keys(raw_full_json).length === 0) {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              law_id,
              error: "raw_full_json field is empty or not available",
              meta: source.meta || {},
            }, null, 2),
          },
        ],
      };
    }

    if (raw_full_json.omitted) {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              law_id,
              error: "raw_full_json was omitted due to size constraints",
              note: "This document's full JSON structure was not stored",
              meta: source.meta || {},
            }, null, 2),
          },
        ],
      };
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            law_id,
            meta: source.meta || {},
            raw_full_json,
          }, null, 2),
        },
      ],
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    logger.info("Legal MCP Server running on stdio");
    await this.logIndexState();
  }
}

const server = new LegalMcpServer();
server.run().catch((error) => {
  logger.error("Server error:", error);
  process.exit(1);
});
