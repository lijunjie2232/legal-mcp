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
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: "search_laws",
          description: "Search for Japanese laws and regulations based on a natural language query.",
          inputSchema: {
            type: "object",
            properties: {
              query: { type: "string", description: "The search terms (e.g., 'Constitution', 'Tax', 'Data Privacy')." },
              era: { type: "string", description: "Optional filter for the Japanese Era (e.g., 'Showa', 'Heisei', 'Reiwa')." },
              law_type: { type: "string", description: "Optional filter for law type (e.g., 'Act', 'CabinetOrder', 'MinisterialOrdinance')." },
              limit: { type: "number", description: "Maximum number of results to return (default is 5).", default: 5 },
            },
            required: ["query"],
          },
        },
        {
          name: "get_law_by_id",
          description: "Retrieve the full details of a specific law by its ID.",
          inputSchema: {
            type: "object",
            properties: {
              law_id: { type: "string", description: "The unique identifier of the law (e.g., '101AC0000000001')." },
            },
            required: ["law_id"],
          },
        },
        {
          name: "get_cluster_status",
          description: "Get the current health and status of the legal document database.",
          inputSchema: {
            type: "object",
            properties: {},
          },
        },
        {
          name: "get_index_state",
          description: "Get detailed statistics and settings of the legal documents index.",
          inputSchema: {
            type: "object",
            properties: {},
          },
        },
        {
          name: "get_raw_json_by_id",
          description: "Retrieve the complete raw_full_json data for a specific law by its ID.",
          inputSchema: {
            type: "object",
            properties: {
              law_id: { type: "string", description: "The unique identifier of the law (e.g., '101AC0000000001')." },
            },
            required: ["law_id"],
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        switch (request.params.name) {
          case "search_laws":
            return await this.handleSearchLaws(request.params.arguments);
          case "get_law_by_id":
            return await this.handleGetLawById(request.params.arguments);
          case "get_cluster_status":
            return await this.handleGetClusterStatus();
          case "get_index_state":
            return await this.handleGetIndexState();
          case "get_raw_json_by_id":
            return await this.handleGetRawJsonById(request.params.arguments);
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${request.params.name}`
            );
        }
      } catch (error: any) {
        logger.error(`Error in ${request.params.name}:`, error);
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
        content: [{ type: "text", text: "No matching laws found." }],
      };
    }

    const results = hits.map((hit: any) => {
      const source = hit._source;
      const meta = source.meta || {};
      const title = meta.LawTitle_Kanji || "Unknown Title";
      const lawNum = meta.LawNum || "Unknown Num";
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
        snippet = sentence ? (sentence.substring(0, 200) + "...") : "No content available.";
      }

      return `ID: ${lawId}\nTitle: ${title}\nLaw Number: ${lawNum}\nSnippet: ${snippet}\n---`;
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
      `# ${meta.LawTitle_Kanji || "Unknown Law"}`,
      `ID: ${law_id}`,
      `Law Number: ${meta.LawNum}`,
      `Type: ${meta.LawType}`,
      `Era: ${meta.Era} ${meta.Year}`,
      "\n## Legal Content\n",
    ];

    for (const field of ["article_title", "article_caption", "sentence", "enact_statement"]) {
      if (content[field]) {
        output.push(`### ${field.split("_").map((s) => s.charAt(0).toUpperCase() + s.slice(1)).join(" ")}`);
        output.push(content[field]);
        output.push("");
      }
    }

    const raw = source.raw_full_json || {};
    if (raw.omitted) {
      output.push("\n*Note: Full raw JSON structure was omitted for this document due to size.*");
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
