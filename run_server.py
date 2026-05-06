#!/usr/bin/env python3
"""
Example script to run the Legal Document Explorer MCP server.

This demonstrates different ways to start the MCP server.
"""

import sys
from legal_mcp import run_mcp_server, logger


def main():
    """Main entry point for running the MCP server."""
    
    # Parse command line arguments
    transport = "stdio"  # Default transport
    
    if len(sys.argv) > 1:
        transport = sys.argv[1]
    
    # Validate transport option
    valid_transports = ["stdio", "sse", "streamable-http"]
    if transport not in valid_transports:
        logger.error(f"Invalid transport: {transport}")
        logger.info(f"Valid options: {', '.join(valid_transports)}")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Legal Document Explorer MCP Server")
    logger.info("=" * 60)
    logger.info(f"Transport: {transport}")
    logger.info("")
    logger.info("Available tools:")
    logger.info("  - search_laws: Search for Japanese laws and regulations")
    logger.info("  - get_law_by_id: Get full details of a law by ID")
    logger.info("  - get_raw_json_by_id: Get complete raw JSON data by ID")
    logger.info("  - get_cluster_status: Get Elasticsearch cluster status")
    logger.info("")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 60)
    
    try:
        # Run the MCP server
        run_mcp_server(transport=transport)
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
