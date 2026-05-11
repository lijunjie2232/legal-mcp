#!/usr/bin/env python3
"""
Convert XML files to JSON format using xmltodict with multiprocessing.
Preserves the directory structure from source to destination.
"""

import os
import json
import xmltodict
from multiprocessing import Pool, cpu_count
from pathlib import Path
import logging
from typing import Tuple
import time
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_xml_files(source_dir: str) -> list:
    """
    Recursively find all XML files in the source directory.
    
    Args:
        source_dir: Path to the source directory containing XML files
        
    Returns:
        List of tuples (source_path, relative_path)
    """
    xml_files = []
    source_path = Path(source_dir)
    
    for xml_file in list(source_path.rglob("*.xml")):
        if xml_file.is_file():
            # Calculate relative path from source directory
            relative_path = xml_file.relative_to(source_path)
            xml_files.append((str(xml_file), str(relative_path)))
    
    return xml_files


def convert_xml_to_json(args: Tuple[str, str, str, str, bool]) -> Tuple[bool, str]:
    """
    Convert a single XML file to JSON.
    
    Args:
        args: Tuple of (source_file, relative_path, source_dir, dest_dir, keep_structure)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    source_file, relative_path, source_dir, dest_dir, keep_structure = args
    
    try:
        # Construct destination path
        if keep_structure:
            dest_path = Path(dest_dir) / relative_path
            # Change extension to .json
            dest_path = dest_path.with_suffix('.json')
        else:
            # Flatten structure: use only the filename
            dest_path = Path(dest_dir) / Path(relative_path).with_suffix('.json').name
        
        # Create destination directory if it doesn't exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read and parse XML file
        with open(source_file, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Convert XML to ordered dict
        data_dict = xmltodict.parse(xml_content, attr_prefix='', force_cdata=False, encoding='utf-8')
        
        # Write JSON file
        with open(dest_path, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=2)
        
        return True, f"Converted: {relative_path}"
    
    except Exception as e:
        return False, f"Error converting {relative_path}: {str(e)}"


def main():
    """Main function to orchestrate the XML to JSON conversion."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert XML files to JSON format')
    parser.add_argument('-s', '--source-dir', default='all_xml',
                        help='Source directory containing XML files')
    parser.add_argument('-d', '--dest-dir', default='all_json',
                        help='Destination directory for JSON files')
    parser.add_argument('-f', '--no-keep-structure', '--flatten', action='store_true',
                        help='Do not preserve directory structure; write all JSON files directly to output directory')
    
    args = parser.parse_args()
    
    source_dir = args.source_dir
    dest_dir = args.dest_dir
    keep_structure = not args.no_keep_structure
    
    # Validate source directory
    if not os.path.exists(source_dir):
        logger.error(f"Source directory does not exist: {source_dir}")
        return
    
    # Find all XML files
    logger.info(f"Searching for XML files in: {source_dir}")
    xml_files = find_xml_files(source_dir)
    
    if not xml_files:
        logger.warning("No XML files found!")
        return
    
    logger.info(f"Found {len(xml_files)} XML files")
    
    # Prepare arguments for multiprocessing
    tasks = [
        (source_file, relative_path, source_dir, dest_dir, keep_structure)
        for source_file, relative_path in xml_files
    ]
    
    # Determine number of processes to use
    num_processes = min(cpu_count(), len(tasks))
    logger.info(f"Using {num_processes} processes for conversion")
    
    # Create destination directory
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    
    # Start timing
    start_time = time.time()
    
    # Process files using multiprocessing pool
    success_count = 0
    error_count = 0
    
    with Pool(processes=num_processes) as pool:
        results = pool.imap_unordered(convert_xml_to_json, tasks)
        
        for idx, (success, message) in enumerate(results, 1):
            if success:
                success_count += 1
                if idx % 100 == 0 or idx == len(tasks):
                    logger.info(f"Progress: {idx}/{len(tasks)} files processed")
            else:
                error_count += 1
                logger.error(message)
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Summary
    logger.info("=" * 60)
    logger.info("Conversion Complete!")
    logger.info(f"Total files: {len(tasks)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Errors: {error_count}")
    logger.info(f"Time elapsed: {elapsed_time:.2f} seconds")
    logger.info(f"Average speed: {len(tasks)/elapsed_time:.2f} files/second")
    logger.info(f"Output directory: {dest_dir}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
