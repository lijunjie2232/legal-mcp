import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import yaml from 'js-yaml';
import { z } from 'zod';

const ElasticsearchConfigSchema = z.object({
  host: z.string().default(''),
  port: z.number().default(0),
  scheme: z.string().default(''),
  user: z.string().default('llm_searcher'),
  password: z.string().default('llm_searcher'),
});

const IndexConfigSchema = z.object({
  name: z.string().default('legal_documents'),
});

const LogConfigSchema = z.object({
  level: z.string().default('INFO'),
  file: z.string().optional(),
});

const AppConfigSchema = z.object({
  es: ElasticsearchConfigSchema.default({}),
  index: IndexConfigSchema.default({}),
  log: LogConfigSchema.default({}),
});

export type AppConfig = z.infer<typeof AppConfigSchema>;

/**
 * Load configuration from YAML file.
 * @param configPath 
 * @returns 
 */
export function loadConfig(configPath?: string): AppConfig {
  const __dirname = path.dirname(fileURLToPath(import.meta.url));
  // src is in js_legal/src, build is in js_legal/build. 
  // Root is two levels up from either.
  const defaultPath = path.resolve(__dirname, '..', '..', 'config.yaml');
  const actualPath = configPath || defaultPath;

  if (!fs.existsSync(actualPath)) {
    console.warn(`Config file not found at ${actualPath}, using defaults.`);
    return AppConfigSchema.parse({});
  }

  try {
    const fileContents = fs.readFileSync(actualPath, 'utf8');
    const data = yaml.load(fileContents);
    return AppConfigSchema.parse(data || {});
  } catch (error) {
    console.error(`Error loading config from ${actualPath}:`, error);
    return AppConfigSchema.parse({});
  }
}
