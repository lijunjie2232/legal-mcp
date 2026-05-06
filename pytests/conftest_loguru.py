"""
Pytest plugin to integrate loguru with pytest.
"""
import sys
import pytest
from loguru import logger


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
