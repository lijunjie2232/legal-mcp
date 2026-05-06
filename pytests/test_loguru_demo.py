"""
Demo script to show loguru integration in tests.
"""
import pytest
from loguru import logger


def test_loguru_demo():
    """Demonstrate loguru usage in tests."""
    logger.info("This is an info message")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.success("This is a success message")
    
    # Test with actual assertion
    assert True
    logger.success("Test passed successfully!")


if __name__ == "__main__":
    test_loguru_demo()
