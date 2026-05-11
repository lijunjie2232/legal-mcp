"""
Elasticsearch import script for legal JSON data.
Cleans JSON files and imports them to Elasticsearch with proper mapping.
"""

import json
import os
import glob
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm

from schema_extractor import clean_json_dict
from es_config import (
    ES_HOST, ES_PORT, ES_SCHEME, ES_USER, ES_PASSWORD,
    INDEX_NAME, MAPPING_FILE,
    BATCH_SIZE, MAX_CHUNK_BYTES, MAX_RETRIES, MAX_RAW_SIZE,
    JSON_DIRECTORY,
    LOG_FILE, LOG_LEVEL
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_es_client() -> Elasticsearch:
    """Create and return Elasticsearch client with retry logic."""
    es = Elasticsearch(
        hosts=[{"host": ES_HOST, "port": ES_PORT, "scheme": ES_SCHEME}],
        basic_auth=(ES_USER, ES_PASSWORD),
        request_timeout=60,
        max_retries=MAX_RETRIES,
        retry_on_status=[429, 502, 503, 504]
    )
    
    # Test connection
    if not es.ping():
        raise ConnectionError(f"Cannot connect to Elasticsearch at {ES_HOST}:{ES_PORT}")
    
    logger.info(f"Connected to Elasticsearch at {ES_HOST}:{ES_PORT}")
    return es


def setup_index(es: Elasticsearch, index_name: str = INDEX_NAME):
    """Create index with mapping if it doesn't exist."""
    # Load mapping
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    # Check if index exists
    if es.indices.exists(index=index_name):
        logger.info(f"Index '{index_name}' already exists")
    else:
        # Create index with mapping
        es.indices.create(index=index_name, body=mapping)
        logger.info(f"Created index '{index_name}' with mapping")


def extract_law_id_from_filename(filename: str) -> str:
    """Extract law ID from filename."""
    # Remove .json extension
    base_name = os.path.splitext(os.path.basename(filename))[0]
    return base_name


def transform_to_es_document(file_path: str, cleaned_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform cleaned JSON data to Elasticsearch document format.
    
    Expected structure based on mapping:
    - law_id: keyword
    - file_name: keyword
    - indexed_at: date
    - schema_version: keyword
    - meta: object with Era, Year, Num, LawType, Lang, etc.
    - legal_content: object with sentence, enact_statement, article_caption, etc.
    - raw_structure: flattened (stores the entire cleaned structure)
    """
    law_id = extract_law_id_from_filename(file_path)
    
    # Extract meta information from Law section
    law_data = cleaned_data.get('Law', {})
    
    meta = {
        'Era': law_data.get('Era'),
        'Year': _safe_int(law_data.get('Year')),
        'Num': law_data.get('Num'),
        'LawType': law_data.get('LawType'),
        'Lang': law_data.get('Lang'),
        'PromulgateMonth': _safe_int(law_data.get('PromulgateMonth')),
        'PromulgateDay': _safe_int(law_data.get('PromulgateDay')),
        'LawNum': law_data.get('LawNum'),
    }
    
    # Extract LawTitle fields from LawBody
    law_body = law_data.get('LawBody', {})
    if isinstance(law_body, dict):
        law_title = law_body.get('LawTitle', {})
        if isinstance(law_title, dict):
            meta['LawTitle_Kanji'] = law_title.get('Kanji')
            meta['LawTitle_Kana'] = law_title.get('Kana')
            meta['LawTitle_Abbrev'] = law_title.get('Abbrev')
    
    # Extract legal content - search for specific fields in the structure
    legal_content = extract_legal_content(cleaned_data)
    
    # Convert lists to strings (join with space)
    for key in legal_content:
        if isinstance(legal_content[key], list):
            legal_content[key] = ' '.join(legal_content[key])
    
    # Build document
    doc = {
        'law_id': law_id,
        'file_name': os.path.basename(file_path),
        'indexed_at': datetime.now(timezone.utc).isoformat(),
        'schema_version': '1.0',
        'meta': {k: v for k, v in meta.items() if v is not None},
        'legal_content': legal_content,
        'raw_full_json': cleaned_data  # Store entire structure (matches mapping)
    }
    
    return doc


def _safe_int(value: Any) -> Optional[int]:
    """Safely convert value to int."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def extract_legal_content(data: Dict[str, Any], legal_content: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Recursively extract legal content fields from the data structure.
    Looks for Sentence, EnactStatement, ArticleCaption, ArticleTitle, etc.
    """
    if legal_content is None:
        legal_content = {}
    
    if isinstance(data, dict):
        for key, value in data.items():
            # Map field names to legal_content fields
            if key == 'Sentence' and isinstance(value, str):
                if 'sentence' not in legal_content:
                    legal_content['sentence'] = []
                if isinstance(legal_content['sentence'], list):
                    legal_content['sentence'].append(value)
            
            elif key == 'EnactStatement' and isinstance(value, str):
                if 'enact_statement' not in legal_content:
                    legal_content['enact_statement'] = []
                if isinstance(legal_content['enact_statement'], list):
                    legal_content['enact_statement'].append(value)
            
            elif key == 'ArticleCaption' and isinstance(value, str):
                if 'article_caption' not in legal_content:
                    legal_content['article_caption'] = []
                if isinstance(legal_content['article_caption'], list):
                    legal_content['article_caption'].append(value)
            
            elif key == 'ArticleTitle' and isinstance(value, str):
                if 'article_title' not in legal_content:
                    legal_content['article_title'] = []
                if isinstance(legal_content['article_title'], list):
                    legal_content['article_title'].append(value)
            
            elif key == 'AppdxTableTitle' and isinstance(value, str):
                if 'appdx_table_title' not in legal_content:
                    legal_content['appdx_table_title'] = []
                if isinstance(legal_content['appdx_table_title'], list):
                    legal_content['appdx_table_title'].append(value)
            
            elif key == 'FigStructTitle' and isinstance(value, str):
                if 'fig_struct_title' not in legal_content:
                    legal_content['fig_struct_title'] = []
                if isinstance(legal_content['fig_struct_title'], list):
                    legal_content['fig_struct_title'].append(value)
            
            # Recurse into nested structures
            elif isinstance(value, (dict, list)):
                extract_legal_content(value, legal_content)
    
    elif isinstance(data, list):
        for item in data:
            extract_legal_content(item, legal_content)
    
    return legal_content


def generate_actions(json_files: List[str], index_name: str):
    """Generator to load, clean, and transform JSON files into ES actions."""
    for file_path in json_files:
        try:
            file_size = os.path.getsize(file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            cleaned_data = clean_json_dict(raw_data)
            doc = transform_to_es_document(file_path, cleaned_data)
            
            # If the original file is too large, omit the raw_full_json to save memory in ES buffer
            if file_size > MAX_RAW_SIZE:
                logger.info(f"Omitting raw_full_json for {os.path.basename(file_path)} (Size: {file_size/1024/1024:.2f}MB)")
                doc['raw_full_json'] = {
                    "omitted": True,
                    "reason": "Original file size exceeds MAX_RAW_SIZE threshold",
                    "original_size_bytes": file_size
                }
            
            yield {
                '_index': index_name,
                '_id': doc['law_id'],
                '_source': doc
            }
        except Exception as e:
            logger.error(f"Error preparing action for {file_path}: {str(e)}")


def process_and_import(es: Elasticsearch, json_files: List[str], index_name: str = INDEX_NAME):
    """Process JSON files and bulk import to Elasticsearch using parallel_bulk."""
    logger.info(f"Starting import of {len(json_files)} files...")
    
    success_count = 0
    error_count = 0
    failed_ids = []

    # thread_count=1 is safer for small ES indexing buffers (e.g. 51MB)
    bulk_kwargs = {
        "chunk_size": BATCH_SIZE,
        "max_chunk_bytes": MAX_CHUNK_BYTES,
        "thread_count": 1,
        "queue_size": 2,
        "raise_on_error": False,
        "raise_on_exception": False,
    }

    with tqdm(total=len(json_files), desc="Importing", unit="doc") as pbar:
        for success, info in helpers.parallel_bulk(es, generate_actions(json_files, index_name), **bulk_kwargs):
            if success:
                success_count += 1
            else:
                error_count += 1
                op_type = list(info.keys())[0]
                error_info = info[op_type]
                doc_id = error_info.get('_id', 'unknown')
                failed_ids.append(doc_id)
                logger.error(f"Failed to index document {doc_id}: {error_info.get('error')}")
            
            pbar.update(1)
            pbar.set_postfix({'success': success_count, 'errors': error_count})

    logger.info(f"Import completed: {success_count} succeeded, {error_count} failed")
    
    # Refresh to ensure count is accurate
    es.indices.refresh(index=index_name)
    total_in_es = es.count(index=index_name)['count']
    logger.info(f"Total documents in index '{index_name}': {total_in_es}")

    if error_count > 0:
        logger.warning(f"⚠️ {error_count} documents failed to import. Check logs for details.")
        if failed_ids:
            logger.warning(f"First 10 failed IDs: {failed_ids[:10]}")


def main():
    """Main execution function."""
    logger.info("Starting Elasticsearch import pipeline...")
    
    # Get all JSON files from test_json directory
    json_files = glob.glob(f'{JSON_DIRECTORY}/*.json')
    logger.info(f"Found {len(json_files)} JSON files in {JSON_DIRECTORY}/")
    
    if not json_files:
        logger.error("No JSON files found in test_json directory")
        return
    
    try:
        # Connect to Elasticsearch
        es = get_es_client()
        
        # Setup index with mapping
        setup_index(es)
        
        # Process and import documents
        process_and_import(es, json_files)
        
        # Refresh index to make documents searchable immediately
        es.indices.refresh(index=INDEX_NAME)
        
        # Get document count
        count = es.count(index=INDEX_NAME)['count']
        logger.info(f"Total documents in index '{INDEX_NAME}': {count}")
        
        logger.info("Elasticsearch import pipeline completed successfully!")
    
    except Exception as e:
        logger.error(f"Import pipeline failed: {str(e)}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
