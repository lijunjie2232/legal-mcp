"""
Pytest configuration and fixtures for legal_mcp tests.
"""

import sys
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from loguru import logger


@pytest.fixture
def mock_es_client():
    """Create a mock Elasticsearch client."""
    # Patch in both locations where es_client might be accessed
    with patch('legal_mcp.mcp_server.es_client') as mock_client:
        yield mock_client


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    with patch('legal_mcp.settings') as mock_settings:
        mock_settings.ES_HOST = "localhost"
        mock_settings.ES_PORT = 9200
        mock_settings.ES_SCHEME = "http"
        mock_settings.ES_USER = "elastic"
        mock_settings.ES_PASSWORD = "test_password"
        mock_settings.INDEX_NAME = "test_legal_documents"
        mock_settings.LOG_LEVEL = "DEBUG"
        mock_settings.LOG_FILE = None
        yield mock_settings


@pytest.fixture
def sample_law_data():
    """Sample law document data for testing."""
    return {
        "_source": {
            "law_id": "419AC1000000051_20260521_504AC0000000048",
            "meta": {
                "LawTitle_Kanji": "日本国憲法の改正手続に関する法律",
                "LawTitle_Kana": "にほんこくけんぽうのかいせいてつづきにかんするほうりつ",
                "LawNum": "平成十九年法律第五十一号",
                "LawType": "Act",
                "Era": "Heisei",
                "Year": 19,
            },
            "legal_content": {
                "sentence": "この法律は、日本国憲法第九十六条に定める日本国憲法の改正について規定する。",
                "article_title": "第一章 総則",
                "article_caption": "第一条 目的",
            },
            "raw_full_json": {
                "Law": {
                    "Era": "Heisei",
                    "LawType": "Act",
                    "LawBody": {
                        "LawTitle": {
                            "Kanji": "日本国憲法の改正手続に関する法律"
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_search_response(sample_law_data):
    """Sample search response from Elasticsearch."""
    return {
        "hits": {
            "hits": [
                {
                    **sample_law_data,
                    "highlight": {
                        "legal_content.sentence": [
                            "この法律は、日本国<em>憲法</em>第九十六条に定める日本国<em>憲法</em>の改正について規定する。"
                        ]
                    }
                }
            ],
            "total": {"value": 1}
        }
    }


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def run_async(coro):
    """Helper to run async functions in tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def pytest_configure(config):
    """Configure loguru for pytest."""
    # Remove default handler
    logger.remove()
    
    # Add console handler with colorized output for tests
    logger.add(
        sys.stderr,
        level="DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    
    # Make logger available in test functions
    config._loguru_logger = logger


@pytest.fixture
def loguru_logger():
    """Provide loguru logger instance to tests."""
    return logger
