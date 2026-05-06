"""
Legal MCP Server Module

This module provides a Model Context Protocol (MCP) server for exploring
and searching Japanese legal documents stored in Elasticsearch.
"""

from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent

# Import settings first to get log configuration
from .mcp_config import AppConfig
from .mcp_util import setup_logger

# Initialize settings as singleton
_settings_instance = None


def get_settings() -> AppConfig:
    """
    Get the singleton AppConfig instance.

    Returns:
        AppConfig: The singleton settings instance
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = AppConfig.from_yaml(MODULE_PATH.parent / "config.yaml")
    return _settings_instance


# Initialize settings and logger
settings = get_settings()
logger = setup_logger(settings)

# Log initialization
logger.info("Legal MCP Server module initialized")
logger.debug(
    f"Configuration loaded - ES_HOST: {settings.es.host}, ES_PORT: {settings.es.port}, INDEX_NAME: {settings.index.name}"
)
logger.debug(
    f"Log configuration - LOG_LEVEL: {settings.log.level}, LOG_FILE: {settings.log.file or 'None'}"
)

# Export individual settings for backward compatibility
# ES_HOST = settings.es.host
# ES_PORT = settings.es.port
# ES_SCHEME = settings.es.scheme
# ES_USER = settings.es.user
# ES_PASSWORD = settings.es.password
INDEX_NAME = settings.index.name

from .mcp_util import get_es_client

# Initialize Elasticsearch client
es_client = get_es_client(
    settings.es.host,
    settings.es.port,
    settings.es.user,
    settings.es.password,
    settings.es.scheme,
)

# Initialize FastMCP server
logger.info("Initializing Legal Document Explorer MCP server")

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Legal Document Explorer")

logger.info("Registering MCP tools")
from .mcp_runner import run_mcp_server
from .mcp_server import (
    get_cluster_status,
    get_law_by_id,
    get_raw_json_by_id,
    search_laws,
)

__all__ = [
    "logger",
    "get_settings",
    "es_client",
    "mcp",
    "search_laws",
    "get_law_by_id",
    "get_raw_json_by_id",
    "get_cluster_status",
    "run_mcp_server",
]
