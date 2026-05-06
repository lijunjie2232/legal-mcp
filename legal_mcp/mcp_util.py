import sys
from pathlib import Path

from .mcp_config import AppConfig


def setup_logger(settings):
    """
    Setup loguru logger with configuration from config.yaml file.

    Args:
        settings: AppConfig instance containing log configuration
    """
    from loguru import logger

    # Remove default handler
    logger.remove()

    # Add console handler with colorized output
    logger.add(
        sys.stderr,
        level=settings.log.level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    # Add file handler if LOG_FILE is specified
    if settings.log.file:
        log_file_path = Path(settings.log.file)
        logger.add(
            log_file_path,
            level=settings.log.level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",  # Rotate log file when it reaches 10 MB
            retention="30 days",  # Keep log files for 30 days
            compression="zip",  # Compress rotated log files
            encoding="utf-8",
        )
        logger.info(f"Log file configured: {log_file_path}")

    return logger


def get_es_client(
    ES_HOST,
    ES_PORT,
    ES_USER,
    ES_PASSWORD,
    ES_SCHEME,
) -> Elasticsearch:
    """Create and return Elasticsearch client."""
    from elasticsearch import Elasticsearch

    from . import logger

    # Check if ES_HOST already contains a full URL with scheme
    if ES_HOST.startswith(("http://", "https://")):
        # Use the full URL directly
        hosts = [ES_HOST]
        logger.info(
            f"Connecting to Elasticsearch at {ES_HOST}"
            + (f":{ES_PORT}" if ES_PORT else "")
        )
    else:
        # Build the connection string from components
        hosts_dict = {"host": ES_HOST}
        if ES_PORT:
            hosts_dict["port"] = ES_PORT
        if ES_SCHEME:
            hosts_dict["scheme"] = ES_SCHEME
        hosts = [hosts_dict]
        logger.info(f"Connecting to Elasticsearch at {ES_SCHEME}://{ES_HOST}:{ES_PORT}")

    es = Elasticsearch(
        hosts=hosts,
        basic_auth=(ES_USER, ES_PASSWORD),
        request_timeout=30,
    )

    # Query and print Elasticsearch index state
    try:
        # Get index information instead of cluster info (due to limited permissions)
        from . import INDEX_NAME

        # Check if index exists and get its stats
        if es.indices.exists(index=INDEX_NAME):
            index_stats = es.indices.stats(index=INDEX_NAME)
            doc_count = index_stats["indices"][INDEX_NAME]["total"]["docs"]["count"]
            store_size = index_stats["indices"][INDEX_NAME]["total"]["store"][
                "size_in_bytes"
            ]

            logger.info(
                f"Elasticsearch index '{INDEX_NAME}' state: "
                f"documents={doc_count}, "
                f"store_size={store_size} bytes"
            )

            # Get index settings
            index_settings = es.indices.get_settings(index=INDEX_NAME)
            number_of_shards = index_settings[INDEX_NAME]["settings"]["index"][
                "number_of_shards"
            ]
            number_of_replicas = index_settings[INDEX_NAME]["settings"]["index"][
                "number_of_replicas"
            ]

            logger.info(
                f"Index settings: shards={number_of_shards}, replicas={number_of_replicas}"
            )
        else:
            logger.warning(f"Index '{INDEX_NAME}' does not exist")
    except Exception as e:
        logger.error(f"Failed to get Elasticsearch index state: {e}")

    logger.info("Elasticsearch client created successfully")
    return es
