"""
Elasticsearch configuration for legal data import.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel

from . import MODULE_PATH


class ElasticsearchConfig(BaseModel):
    """Elasticsearch connection configuration."""

    host: str = ""
    port: int = 0
    scheme: str = ""
    user: str = "llm_searcher"
    password: str = "llm_searcher"


class IndexConfig(BaseModel):
    """Index configuration."""

    name: str = "legal_documents"


class LogConfig(BaseModel):
    """Log configuration."""

    level: str = "INFO"
    file: str | None = None  # no log file by default


class AppConfig(BaseModel):
    """Application configuration loaded from config.yaml file."""

    es: ElasticsearchConfig = ElasticsearchConfig()
    index: IndexConfig = IndexConfig()
    log: LogConfig = LogConfig()

    @classmethod
    def from_yaml(
        cls, yaml_path: str = MODULE_PATH.parent / "config.yaml"
    ) -> "AppConfig":
        """Load configuration from YAML file."""
        config_path = Path(yaml_path)
        if not config_path.exists():
            # If config file doesn't exist, return default config
            return cls()

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        if config_data is None:
            return cls()

        return cls(**config_data)
