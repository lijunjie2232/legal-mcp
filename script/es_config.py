"""
Elasticsearch configuration for legal data import.
"""

# Elasticsearch connection settings
ES_HOST = "localhost"
ES_PORT = 9200
ES_SCHEME = "http"
ES_USER = "elastic"
ES_PASSWORD = "elawstic"

# Index settings
INDEX_NAME = "legal_documents"
MAPPING_FILE = "elasticsearch_index_mapping.json"

# Import settings
BATCH_SIZE = 50
MAX_CHUNK_BYTES = 10 * 1024 * 1024  # 10MB limit for bulk requests
MAX_RETRIES = 5
MAX_RAW_SIZE = 5 * 1024 * 1024  # 5MB limit for raw JSON storage
JSON_DIRECTORY = "../data/all_json"

# Logging settings
LOG_FILE = "es_import.log"
LOG_LEVEL = "INFO"