"""
Tests for legal_mcp configuration and settings.
"""

import pytest
from legal_mcp import get_settings, settings
from loguru import logger


class TestSettings:
    """Test suite for Elasticsearch settings."""

    def test_settings_singleton(self):
        """Test that settings returns the same instance (singleton pattern)."""
        logger.info("Starting test_settings_singleton")
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2, "Settings should be a singleton"
        logger.success("test_settings_singleton passed successfully")

    def test_settings_has_required_fields(self):
        """Test that settings has all required fields."""
        logger.info("Starting test_settings_has_required_fields")
        assert hasattr(settings, 'ES_HOST')
        assert hasattr(settings, 'ES_PORT')
        assert hasattr(settings, 'ES_SCHEME')
        assert hasattr(settings, 'ES_USER')
        assert hasattr(settings, 'ES_PASSWORD')
        assert hasattr(settings, 'INDEX_NAME')
        assert hasattr(settings, 'LOG_LEVEL')
        assert hasattr(settings, 'LOG_FILE')
        logger.success("test_settings_has_required_fields passed successfully")

    def test_settings_default_values(self):
        """Test settings default values."""
        logger.info("Starting test_settings_default_values")
        assert isinstance(settings.ES_HOST, str)
        assert isinstance(settings.ES_PORT, int)
        assert isinstance(settings.INDEX_NAME, str)
        logger.success("test_settings_default_values passed successfully")

    def test_es_port_is_integer(self):
        """Test that ES_PORT is an integer."""
        logger.info("Starting test_es_port_is_integer")
        assert isinstance(settings.ES_PORT, int)
        assert settings.ES_PORT > 0
        logger.success("test_es_port_is_integer passed successfully")

    def test_index_name_is_string(self):
        """Test that INDEX_NAME is a non-empty string."""
        logger.info("Starting test_index_name_is_string")
        assert isinstance(settings.INDEX_NAME, str)
        assert len(settings.INDEX_NAME) > 0
        logger.success("test_index_name_is_string passed successfully")


class TestLogger:
    """Test suite for logger configuration."""

    def test_logger_exists(self):
        """Test that logger is initialized."""
        from legal_mcp import logger as legal_logger
        logger.info("Starting test_logger_exists")
        assert legal_logger is not None
        logger.success("test_logger_exists passed successfully")

    def test_logger_has_handlers(self):
        """Test that logger has at least one handler."""
        from legal_mcp import logger as legal_logger
        logger.info("Starting test_logger_has_handlers")
        assert len(legal_logger._core.handlers) > 0
        logger.success("test_logger_has_handlers passed successfully")

    def test_logger_can_log(self):
        """Test that logger can log messages without errors."""
        from legal_mcp import logger as legal_logger
        logger.info("Starting test_logger_can_log")
        # This should not raise any exceptions
        legal_logger.debug("Test debug message")
        legal_logger.info("Test info message")
        legal_logger.warning("Test warning message")
        logger.success("test_logger_can_log passed successfully")
