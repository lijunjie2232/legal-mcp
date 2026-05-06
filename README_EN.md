# Japanese Legal MCP Server

[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-repository-black.svg)](https://github.com/lijunjie2232/legal-mcp)

[![English](https://img.shields.io/badge/English-US-blue.svg)](README_EN.md)
[![日文](https://img.shields.io/badge/日本語-JA-blue.svg)](README.md)

A Model Context Protocol (MCP) server for exploring and searching Japanese legal documents stored in Elasticsearch. This server provides tools to search, retrieve, and analyze Japanese laws and regulations with advanced features like smart highlighting and raw JSON access.

## Features

- 🔍 **Search Japanese Laws**: Natural language search across Japanese legal documents with multi-field matching
- 📄 **Retrieve Full Documents**: Get complete law details by ID with formatted output
- 💾 **Access Raw JSON**: Retrieve full raw JSON data structure including nested fields
- 📊 **Cluster Monitoring**: Check Elasticsearch cluster health and status
- 🎯 **Smart Highlighting**: Intelligent snippet extraction with highlighted matches from multiple fields
- ⚡ **Async Support**: Full async/await support for better performance
- 🌐 **Multiple Transports**: Support for stdio, SSE, and streamable HTTP transports
- 📝 **Configurable Logging**: Loguru-based logging with console and file output options

## Installation

### Fast Installation

Use `curl` or `wget` to download and execute the installation script:

```bash
# Using curl
bash -c "$(curl -fsSL https://raw.githubusercontent.com/lijunjie2232/legal-mcp/refs/heads/master/install.sh)"
```

```bash
# Using wget
bash -c "$(wget https://raw.githubusercontent.com/lijunjie2232/legal-mcp/refs/heads/master/install.sh -O -)"
```

### From Source

```bash
# Clone the repository
git clone git@github.com:lijunjie2232/legal-mcp.git
cd legal-mcp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Using uv (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone git@github.com:lijunjie2232/legal-mcp.git
cd legal-mcp
uv sync
```

## Configuration

Create a `config.yaml` file in the project root:

```yaml
# Elasticsearch connection settings
es:
  host: "https://l2533584225-elasticsearch-legal-docs.hf.space"
  # port: 9200
  # scheme: "https"
  user: "llm_searcher"
  password: "llm_searcher"

# Index settings
index:
  name: "legal_documents"

# Log settings
log:
  level: "INFO"
  # file: "/path/to/logfile.log"  # Uncomment to enable file logging
```

The configuration system uses Pydantic models for validation and supports loading from YAML files. Default values are provided if no config file exists.

## Usage

### Command Line

```bash
# Start the MCP server (default: stdio transport)
legal-mcp

# With specific transport
legal-mcp stdio              # Standard input/output (for Claude Desktop)
legal-mcp sse                # Server-Sent Events (for web-based clients)
legal-mcp streamable-http    # HTTP streaming

# Show help
legal-mcp --help
```

### Python API

```python
from legal_mcp import search_laws, get_law_by_id, get_raw_json_by_id, get_cluster_status
import asyncio

async def main():
    # Search for laws with filters
    results = await search_laws("憲法", era="Reiwa", law_type="Act", limit=5)
    print(results)

    # Get full law details
    law = await get_law_by_id("419AC1000000051_20260521_504AC0000000048")
    print(law)

    # Get raw JSON data
    raw_data = await get_raw_json_by_id("419AC1000000051_20260521_504AC0000000048")
    print(raw_data)

    # Check cluster status
    status = await get_cluster_status()
    print(status)

asyncio.run(main())
```

### Running as a Module

```python
from legal_mcp.mcp_runner import run_mcp_server

# Run with stdio transport (default)
run_mcp_server()

# Or run with SSE transport
run_mcp_server(transport="sse")
```

### Available Tools

The MCP server provides these tools:

1. **search_laws**: Search for Japanese laws and regulations
   - Parameters:
     - `query` (str): The search terms (e.g., "Constitution", "Tax", "Data Privacy")
     - `era` (Optional[str]): Filter for Japanese Era (e.g., "Showa", "Heisei", "Reiwa")
     - `law_type` (Optional[str]): Filter for law type (e.g., "Act", "CabinetOrder", "MinisterialOrdinance")
     - `limit` (int): Maximum number of results to return (default: 5)
   - Returns: Formatted string with law ID, title, law number, and relevant snippets
   - Features: Multi-field search with highlighting, smart snippet extraction
2. **get_law_by_id**: Retrieve formatted law details by ID
   - Parameters: `law_id` (str) - The unique identifier of the law
   - Returns: Formatted markdown-style output with metadata and legal content
   - Includes: Law title, number, type, era, year, and structured content sections
3. **get_raw_json_by_id**: Get complete raw JSON data by ID
   - Parameters: `law_id` (str) - The unique identifier of the law
   - Returns: Dictionary containing law_id, meta, and raw_full_json
   - Note: Some documents may have omitted raw JSON due to size constraints
4. **get_cluster_status**: Check Elasticsearch cluster health
   - No parameters required
   - Returns: Dictionary with status, node count, document count, and index name
   - Useful for monitoring and diagnostics

### Architecture Overview

The project follows a modular architecture:

- **`mcp_config.py`**: Configuration management using Pydantic models with YAML support
- **`mcp_util.py`**: Utility functions including logger setup and Elasticsearch client creation
- **`mcp_server.py`**: Core MCP tool implementations (search, retrieval, cluster status)
- **`mcp_runner.py`**: Server runner with support for multiple transport protocols
- **`__init__.py`**: Module initialization with singleton configuration and client setup

Key design patterns:

- Singleton pattern for configuration and Elasticsearch client
- Async/await for all MCP tools
- Structured logging with loguru
- Type hints throughout the codebase

## Elasticsearch Instance

> ⚠️ **ATTENTION**: The demo API for the legal documents Elasticsearch instance is available at [https://l2533584225-elasticsearch-legal-docs.hf.space](https://huggingface.co/spaces/l2533584225/elasticsearch-legal-docs). It may go to sleep after 30 minutes of inactivity, so please activate it before use or build your own Elasticsearch instance.

### Create a Private Elasticsearch Instance

To create your own Elasticsearch instance, there are several options:

1. **On Hugging Face** (using free tier): Create a space and upload the [Dockerfile](https://huggingface.co/spaces/l2533584225/elasticsearch-legal-docs/raw/main/Dockerfile) (the same as the current HF demo).

2. **On a private server**(docker command):
   ```bash
   docker run -d -p 9200:9200 -p 9300:9300 --name elasticsearch-legal-docs lijunjie2232/elasticsearch-legal-docs:latest
   ```
3. **On a private server**(Dockerfile):
   ```bash
   wget https://huggingface.co/spaces/l2533584225/elasticsearch-legal-docs/raw/main/Dockerfile
   docker build -t elasticsearch-legal-docs:dev .
   docker run -d -p 9200:9200 -p 9300:9300 --name elasticsearch-legal-docs elasticsearch-legal-docs:dev
   ```
   For other options on running Elasticsearch with Docker, see the [official documentation](https://www.elastic.co/docs/deploy-manage/deploy/self-managed/install-elasticsearch-docker-basic).

## Project Structure

```
legal-mcp/
├── legal_mcp/              # Main package
│   ├── __init__.py         # Package initialization, singleton config & client
│   ├── mcp_config.py       # Pydantic configuration models
│   ├── mcp_util.py         # Logger setup and ES client utilities
│   ├── mcp_server.py       # MCP tool implementations (4 tools)
│   └── mcp_runner.py       # Server runner with multiple transport support
├── pytests/                # Test suite
│   ├── conftest.py         # Test fixtures and configuration
│   ├── test_config.py      # Configuration tests
│   ├── test_search.py      # Search functionality tests
│   ├── test_retrieval.py   # Document retrieval tests
│   └── test_cluster.py     # Cluster status tests
├── data/                   # Legal document data (JSON/XML)
├── es_data/                # Elasticsearch data directory
├── script/                 # Utility scripts
│   ├── es_import.py        # Elasticsearch import script
│   ├── xml_to_json.py      # XML to JSON conversion
│   └── schema_extractor.py # Schema extraction utilities
├── config.yaml             # YAML configuration file
├── config.example.yaml     # Example configuration template
├── pyproject.toml          # Project metadata and dependencies
├── run_server.py           # Alternative server entry point
└── README.md               # This file
```

## Requirements

- Python 3.14+
- Elasticsearch 9.3+ (with proper index mapping configured)
- Virtual environment (recommended)
- Japanese legal documents in Elasticsearch index

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Legal document data from [e-Gov 法令検索](https://laws.e-gov.go.jp/)
- Built with [Model Context Protocol](https://modelcontextprotocol.io/)
- Powered by [Elasticsearch](https://www.elastic.co/elasticsearch/)
- Uses [FastMCP](https://github.com/jlowin/fastmcp) for MCP server implementation
- Japanese legal document data structure and search optimization

## Troubleshooting

### Common Issues

1. **Connection refused to Elasticsearch**
   - Verify Elasticsearch is running: `curl http://localhost:9200`
   - Check credentials in `config.yaml`
   - Ensure the index exists and has documents

2. **No search results found**
   - Verify the index name matches your Elasticsearch setup
   - Check if documents are properly indexed
   - Try broader search terms

3. **Import errors**
   - Ensure virtual environment is activated
   - Run `pip install -e .` to install in development mode
   - Check Python version (requires 3.14+)

4. **Logging not working**
   - Check log level in `config.yaml`
   - Verify file permissions if using file logging
   - Console logging is enabled by default
