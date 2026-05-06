"""
Tests for legal_mcp search functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from legal_mcp.mcp_server import search_laws
from conftest import run_async
from loguru import logger


class TestSearchLaws:
    """Test suite for search_laws function."""

    @pytest.mark.asyncio
    async def test_search_with_query(self, mock_es_client, sample_search_response):
        """Test search with a query string."""
        logger.info("Starting test_search_with_query")
        mock_es_client.search.return_value = sample_search_response
        
        result = await search_laws("憲法")
        
        assert isinstance(result, str)
        assert "日本国憲法の改正手続に関する法律" in result
        mock_es_client.search.assert_called_once()
        logger.success("test_search_with_query passed successfully")

    @pytest.mark.asyncio
    async def test_search_with_filters(self, mock_es_client, sample_search_response):
        """Test search with era and law_type filters."""
        logger.info("Starting test_search_with_filters")
        mock_es_client.search.return_value = sample_search_response
        
        result = await search_laws("憲法", era="Heisei", law_type="Act")
        
        assert isinstance(result, str)
        # Verify the search was called
        assert mock_es_client.search.called
        # Check that filters were applied
        call_args = mock_es_client.search.call_args
        search_body = call_args[1]['body']
        assert len(search_body['query']['bool']['filter']) == 2
        logger.success("test_search_with_filters passed successfully")

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_es_client):
        """Test search when no results are found."""
        logger.info("Starting test_search_no_results")
        mock_es_client.search.return_value = {"hits": {"hits": []}}
        
        result = await search_laws("nonexistent_query")
        
        assert result == "No matching laws found."
        logger.success("test_search_no_results passed successfully")

    @pytest.mark.asyncio
    async def test_search_with_highlight(self, mock_es_client, sample_search_response):
        """Test that search uses highlight from Elasticsearch response."""
        logger.info("Starting test_search_with_highlight")
        mock_es_client.search.return_value = sample_search_response
        
        result = await search_laws("憲法")
        
        # The result should contain the sentence without highlight tags
        assert "憲法" in result
        assert "<em>" not in result  # Highlight tags should be removed
        logger.success("test_search_with_highlight passed successfully")

    @pytest.mark.asyncio
    async def test_search_error_handling(self, mock_es_client):
        """Test search error handling."""
        logger.info("Starting test_search_error_handling")
        mock_es_client.search.side_effect = Exception("Connection error")
        
        result = await search_laws("test")
        
        assert "error" in result.lower() or "occurred" in result.lower()
        logger.success("test_search_error_handling passed successfully")

    @pytest.mark.asyncio
    async def test_search_limit_parameter(self, mock_es_client, sample_search_response):
        """Test that limit parameter is passed to Elasticsearch."""
        logger.info("Starting test_search_limit_parameter")
        mock_es_client.search.return_value = sample_search_response
        
        await search_laws("test", limit=10)
        
        call_args = mock_es_client.search.call_args
        assert call_args[1]['size'] == 10
        logger.success("test_search_limit_parameter passed successfully")

    def test_search_sync_wrapper(self):
        """Test that search_laws can be called synchronously."""
        logger.info("Starting test_search_sync_wrapper")
        # This tests that the function is properly defined as async
        import inspect
        assert inspect.iscoroutinefunction(search_laws)
        logger.success("test_search_sync_wrapper passed successfully")
