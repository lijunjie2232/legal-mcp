"""
MCP Server Runner Module

This module provides functionality to run the Legal Document Explorer MCP server.
"""

import asyncio

from . import logger, mcp


def run_mcp_server(transport: str = "stdio"):
    """
    Run the Legal Document Explorer MCP server.

    Args:
        transport: The transport protocol to use. Options:
            - "stdio": Standard input/output (default, for Claude Desktop)
            - "sse": Server-Sent Events (for web-based clients)
            - "streamable-http": HTTP streaming

    Example:
        ```python
        from legal_mcp import run_mcp_server

        # Run with stdio transport (default)
        run_mcp_server()

        # Or run with SSE transport
        run_mcp_server(transport="sse")
        ```
    """
    logger.info(
        f"Starting Legal Document Explorer MCP server with {transport} transport"
    )

    try:
        # Run the MCP server
        mcp.run(transport=transport)
        logger.info("MCP server stopped")
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        raise


async def run_mcp_server_async(transport: str = "stdio"):
    """
    Asynchronously run the Legal Document Explorer MCP server.

    Args:
        transport: The transport protocol to use ("stdio", "sse", or "streamable-http")

    Example:
        ```python
        import asyncio
        from legal_mcp import run_mcp_server_async

        asyncio.run(run_mcp_server_async())
        ```
    """
    logger.info(
        f"Starting Legal Document Explorer MCP server (async) with {transport} transport"
    )

    try:
        # Get the appropriate app based on transport
        if transport == "sse":
            app = mcp.sse_app()
            logger.info("SSE app created. Use a web server to serve it.")
            return app
        elif transport == "streamable-http":
            app = mcp.streamable_http_app()
            logger.info("Streamable HTTP app created. Use a web server to serve it.")
            return app
        else:
            # For stdio, run directly
            await mcp.run_async(transport=transport)
            logger.info("MCP server stopped")
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        raise


if __name__ == "__main__":
    import sys

    # Get transport from command line argument if provided
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    logger.info(f"Running MCP server with transport: {transport}")
    run_mcp_server(transport=transport)


def main():
    """
    Main entry point for the legal-mcp command.

    This function is called when running 'legal-mcp' from the command line.
    """
    import sys

    # Show help if requested
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Legal Document Explorer MCP Server")
        print("=" * 60)
        print("")
        print("Usage: legal-mcp [TRANSPORT]")
        print("")
        print("Transport options:")
        print("  stdio              Standard input/output (default)")
        print("  sse                Server-Sent Events")
        print("  streamable-http    HTTP streaming")
        print("")
        print("Examples:")
        print("  legal-mcp                  # Start with stdio (default)")
        print("  legal-mcp stdio            # Start with stdio transport")
        print("  legal-mcp sse              # Start with SSE transport")
        print("")
        print("Available MCP tools:")
        print("  - search_laws: Search for Japanese laws and regulations")
        print("  - get_law_by_id: Get full details of a law by ID")
        print("  - get_raw_json_by_id: Get complete raw JSON data by ID")
        print("  - get_cluster_status: Get Elasticsearch cluster status")
        print("")
        print("Configuration:")
        print(
            "  Create a config.yaml file in the project root with Elasticsearch settings."
        )
        print("")
        print("More info: https://github.com/lijunjie2232/legal-mcp")
        sys.exit(0)

    # Get transport from command line argument if provided
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

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
        run_mcp_server(transport=transport)
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
