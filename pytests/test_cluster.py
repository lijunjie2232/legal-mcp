"""
Tests for legal_mcp cluster status functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from legal_mcp.mcp_server import get_cluster_status
from loguru import logger


class TestGetClusterStatus:
    """Test suite for get_cluster_status function."""

    @pytest.mark.asyncio
    async def test_get_cluster_status_success(self, mock_es_client):
        """Test successful retrieval of cluster status."""
        logger.info("Starting test_get_cluster_status_success")
        from legal_mcp import settings
        
        mock_health = {
            "status": "green",
            "number_of_nodes": 1
        }
        mock_count = {"count": 100}
        
        mock_es_client.cluster.health.return_value = mock_health
        mock_es_client.count.return_value = mock_count
        
        result = await get_cluster_status()
        
        assert isinstance(result, dict)
        assert result["status"] == "green"
        assert result["nodes"] == 1
        assert result["document_count"] == 100
        assert result["index_name"] == settings.INDEX_NAME
        logger.success("test_get_cluster_status_success passed successfully")

    @pytest.mark.asyncio
    async def test_get_cluster_status_yellow(self, mock_es_client):
        """Test cluster status when status is yellow."""
        logger.info("Starting test_get_cluster_status_yellow")
        mock_health = {
            "status": "yellow",
            "number_of_nodes": 1
        }
        mock_count = {"count": 50}
        
        mock_es_client.cluster.health.return_value = mock_health
        mock_es_client.count.return_value = mock_count
        
        result = await get_cluster_status()
        
        assert result["status"] == "yellow"
        logger.success("test_get_cluster_status_yellow passed successfully")

    @pytest.mark.asyncio
    async def test_get_cluster_status_error(self, mock_es_client):
        """Test error handling when cluster status check fails."""
        logger.info("Starting test_get_cluster_status_error")
        mock_es_client.cluster.health.side_effect = Exception("Connection error")
        
        result = await get_cluster_status()
        
        assert "error" in result
        assert "Connection error" in result["error"]
        logger.success("test_get_cluster_status_error passed successfully")

    @pytest.mark.asyncio
    async def test_get_cluster_status_returns_dict(self, mock_es_client):
        """Test that function returns a dictionary."""
        logger.info("Starting test_get_cluster_status_returns_dict")
        mock_health = {"status": "green", "number_of_nodes": 1}
        mock_count = {"count": 0}
        
        mock_es_client.cluster.health.return_value = mock_health
        mock_es_client.count.return_value = mock_count
        
        result = await get_cluster_status()
        
        assert isinstance(result, dict)
        logger.success("test_get_cluster_status_returns_dict passed successfully")

    @pytest.mark.asyncio
    async def test_get_cluster_status_has_required_keys(self, mock_es_client):
        """Test that result has all required keys."""
        logger.info("Starting test_get_cluster_status_has_required_keys")
        mock_health = {"status": "green", "number_of_nodes": 3}
        mock_count = {"count": 1000}
        
        mock_es_client.cluster.health.return_value = mock_health
        mock_es_client.count.return_value = mock_count
        
        result = await get_cluster_status()
        
        required_keys = ["status", "nodes", "document_count", "index_name"]
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"
        logger.success("test_get_cluster_status_has_required_keys passed successfully")
