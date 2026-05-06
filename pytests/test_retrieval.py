"""
Tests for legal_mcp law retrieval functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from legal_mcp.mcp_server import get_law_by_id, get_raw_json_by_id
from loguru import logger


class TestGetLawById:
    """Test suite for get_law_by_id function."""

    @pytest.mark.asyncio
    async def test_get_law_success(self, mock_es_client, sample_law_data):
        """Test successful retrieval of a law by ID."""
        logger.info("Starting test_get_law_success")
        mock_es_client.get.return_value = sample_law_data
        
        result = await get_law_by_id("419AC1000000051_20260521_504AC0000000048")
        
        assert isinstance(result, str)
        assert "日本国憲法の改正手続に関する法律" in result
        assert "平成十九年法律第五十一号" in result
        mock_es_client.get.assert_called_once()
        logger.success("test_get_law_success passed successfully")

    @pytest.mark.asyncio
    async def test_get_law_not_found(self, mock_es_client):
        """Test retrieval when law is not found."""
        logger.info("Starting test_get_law_not_found")
        from elasticsearch import NotFoundError, ApiError
        from elastic_transport import ApiResponseMeta
        
        # Create a proper NotFoundError
        meta = ApiResponseMeta(status=404, headers={}, http_version="1.1", duration=0, node=None)
        error = NotFoundError("Document not found", meta=meta, body={"error": "not_found"})
        mock_es_client.get.side_effect = error
        
        result = await get_law_by_id("NONEXISTENT_ID")
        
        assert "not found" in result.lower() or "error" in result.lower()
        logger.success("test_get_law_not_found passed successfully")

    @pytest.mark.asyncio
    async def test_get_law_error_handling(self, mock_es_client):
        """Test error handling during law retrieval."""
        logger.info("Starting test_get_law_error_handling")
        mock_es_client.get.side_effect = Exception("Connection error")
        
        result = await get_law_by_id("test_id")
        
        assert "error" in result.lower()
        logger.success("test_get_law_error_handling passed successfully")


class TestGetRawJsonById:
    """Test suite for get_raw_json_by_id function."""

    @pytest.mark.asyncio
    async def test_get_raw_json_success(self, mock_es_client, sample_law_data):
        """Test successful retrieval of raw JSON by ID."""
        logger.info("Starting test_get_raw_json_success")
        mock_es_client.get.return_value = sample_law_data
        
        result = await get_raw_json_by_id("419AC1000000051_20260521_504AC0000000048")
        
        assert isinstance(result, dict)
        assert "law_id" in result
        assert "raw_full_json" in result
        assert "meta" in result
        assert result["law_id"] == "419AC1000000051_20260521_504AC0000000048"
        logger.success("test_get_raw_json_success passed successfully")

    @pytest.mark.asyncio
    async def test_get_raw_json_structure(self, mock_es_client, sample_law_data):
        """Test that raw JSON has expected structure."""
        logger.info("Starting test_get_raw_json_structure")
        mock_es_client.get.return_value = sample_law_data
        
        result = await get_raw_json_by_id("test_id")
        
        raw_json = result["raw_full_json"]
        assert isinstance(raw_json, dict)
        assert "Law" in raw_json
        logger.success("test_get_raw_json_structure passed successfully")

    @pytest.mark.asyncio
    async def test_get_raw_json_empty(self, mock_es_client):
        """Test retrieval when raw_full_json is empty."""
        logger.info("Starting test_get_raw_json_empty")
        empty_data = {
            "_source": {
                "law_id": "test_id",
                "meta": {},
                "raw_full_json": {}
            }
        }
        mock_es_client.get.return_value = empty_data
        
        result = await get_raw_json_by_id("test_id")
        
        assert "error" in result
        assert "empty" in result["error"].lower() or "not available" in result["error"].lower()
        logger.success("test_get_raw_json_empty passed successfully")

    @pytest.mark.asyncio
    async def test_get_raw_json_omitted(self, mock_es_client):
        """Test retrieval when raw_full_json was omitted."""
        logger.info("Starting test_get_raw_json_omitted")
        omitted_data = {
            "_source": {
                "law_id": "test_id",
                "meta": {},
                "raw_full_json": {"omitted": True}
            }
        }
        mock_es_client.get.return_value = omitted_data
        
        result = await get_raw_json_by_id("test_id")
        
        assert "error" in result
        assert "omitted" in result["error"].lower()
        logger.success("test_get_raw_json_omitted passed successfully")

    @pytest.mark.asyncio
    async def test_get_raw_json_not_found(self, mock_es_client):
        """Test retrieval when document doesn't exist."""
        logger.info("Starting test_get_raw_json_not_found")
        from elasticsearch import NotFoundError
        from elastic_transport import ApiResponseMeta
        
        # Create a proper NotFoundError
        meta = ApiResponseMeta(status=404, headers={}, http_version="1.1", duration=0, node=None)
        error = NotFoundError("Not found", meta=meta, body={"error": "not_found"})
        mock_es_client.get.side_effect = error
        
        result = await get_raw_json_by_id("NONEXISTENT")
        
        assert "error" in result
        assert "not found" in result["error"].lower() or "error" in result["error"].lower()
        logger.success("test_get_raw_json_not_found passed successfully")

    @pytest.mark.asyncio
    async def test_get_raw_json_returns_dict(self, mock_es_client, sample_law_data):
        """Test that function returns a dictionary."""
        logger.info("Starting test_get_raw_json_returns_dict")
        mock_es_client.get.return_value = sample_law_data
        
        result = await get_raw_json_by_id("test_id")
        
        assert isinstance(result, dict)
        logger.success("test_get_raw_json_returns_dict passed successfully")
