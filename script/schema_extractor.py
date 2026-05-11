"""
Main schema extraction pipeline for JSON files.
Implements multiprocessing for data cleaning, node statistics, and graph construction.
"""

import json
import os
import glob
import logging
import multiprocessing as mp
from multiprocessing import Pool, Manager, Lock, Queue
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import networkx as nx
import pickle

from schema_node import SchemaNode, build_schema_from_dict, merge_schema_nodes, detect_value_type

# Define terminal nodes - these nodes will not be traversed further
# Their values are treated as opaque objects
TERMINAL_NODES = {
    'AppdxTable',
    'AppdxNote', 
    'SupplProvision',
    'Preamble',
    'TOC',
    'AppdxStyle',
    'AppdxFormat',
    'FigStruct',
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('schema_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def clean_json_value(value: Any) -> Any:
    """
    Clean a single JSON value according to the rules:
    - Convert "false"/"true" strings to bool
    - Convert numeric strings to int
    - Handle Sentence fields (extract #text if dict)
    - Handle Paragraph fields (wrap dict in list)
    """
    if isinstance(value, str):
        # Convert boolean strings
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        # Convert numeric strings to int
        else:
            try:
                # Only convert if it's a standard digit string
                if value.isdigit() and all(c in '0123456789' for c in value):
                    return int(value)
            except ValueError:
                pass  # If conversion fails, keep as string
        return value
    elif isinstance(value, dict):
        return clean_json_dict(value)
    elif isinstance(value, list):
        return [clean_json_value(item) for item in value]
    else:
        return value


def clean_json_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively clean a JSON dictionary using iterative stack-based approach.
    Handles special cases for Sentence and Paragraph fields.
    """
    cleaned = {}
    
    # Stack contains tuples of (current_dict, current_cleaned_dict, parent_key)
    stack = [(data, cleaned, None)]
    
    while stack:
        current_dict, current_cleaned, parent_key = stack.pop()
        
        for key, value in current_dict.items():
            # Special handling for LawTitle to keep its structure but rename #text
            if key == "LawTitle" and isinstance(value, dict) and '#text' in value:
                value['Kanji'] = value.pop("#text")
            
            if key != "LawTitle" and isinstance(value, dict) and '#text' in value:
                current_cleaned[key] = value['#text']
                value = value['#text']
                continue
            
            # Special handling for Sentence field
            if key == 'Sentence':
                if isinstance(value, dict):
                    # Extract #text value if it exists
                    if '#text' in value:
                        current_cleaned[key] = value['#text']
                    else:
                        # If no #text, recursively clean the dict
                        cleaned_value = {}
                        stack.append((value, cleaned_value, key))
                        current_cleaned[key] = cleaned_value
                else:
                    current_cleaned[key] = clean_json_value(value)
            
            # Special handling for EnactStatement field - transform to string
            elif key == 'EnactStatement':
                if isinstance(value, dict):
                    # Extract #text value if it exists
                    if '#text' in value:
                        current_cleaned[key] = value['#text']
                    else:
                        # If no #text, recursively clean the dict
                        cleaned_value = {}
                        stack.append((value, cleaned_value, key))
                        current_cleaned[key] = cleaned_value
                elif isinstance(value, list):
                    # Concatenate all sub-items into one string
                    str_parts = []
                    for item in value:
                        if isinstance(item, str):
                            str_parts.append(item)
                        elif isinstance(item, dict):
                            # Extract #text if available, otherwise convert to string
                            if '#text' in item:
                                str_parts.append(item['#text'])
                            else:
                                # Recursively clean and convert to string
                                cleaned_item = {}
                                stack.append((item, cleaned_item, key))
                                str_parts.append(str(cleaned_item))
                        else:
                            str_parts.append(str(item))
                    current_cleaned[key] = ''.join(str_parts)
                else:
                    current_cleaned[key] = clean_json_value(value)
            
            # Special handling for Paragraph field
            elif key == 'Paragraph':
                if isinstance(value, dict):
                    # Wrap dict in a list
                    cleaned_item = {}
                    stack.append((value, cleaned_item, key))
                    current_cleaned[key] = [cleaned_item]
                elif isinstance(value, list):
                    # Clean each item in the list
                    cleaned_list = []
                    for item in value:
                        if isinstance(item, dict):
                            cleaned_item = {}
                            stack.append((item, cleaned_item, key))
                            cleaned_list.append(cleaned_item)
                        else:
                            cleaned_list.append(clean_json_value(item))
                    current_cleaned[key] = cleaned_list
                else:
                    current_cleaned[key] = clean_json_value(value)
            
            else:
                # Regular field - clean normally
                if isinstance(value, dict):
                    cleaned_value = {}
                    stack.append((value, cleaned_value, key))
                    current_cleaned[key] = cleaned_value
                elif isinstance(value, list):
                    cleaned_list = []
                    for item in value:
                        if isinstance(item, dict):
                            cleaned_item = {}
                            stack.append((item, cleaned_item, key))
                            cleaned_list.append(cleaned_item)
                        else:
                            cleaned_list.append(clean_json_value(item))
                    current_cleaned[key] = cleaned_list
                else:
                    current_cleaned[key] = clean_json_value(value)
    
    return cleaned


def process_single_json_file(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Process a single JSON file: read, clean, and return.
    This function is designed to be used with multiprocessing.
    """
    try:
        logger.info(f"Processing file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Clean the data
        cleaned_data = clean_json_dict(data)
        
        return (file_path, cleaned_data)
    
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}", exc_info=True)
        return (file_path, None)


def extract_node_types_from_dict(data: Dict[str, Any], parent_path: str = "") -> Dict[str, str]:
    """
    Extract node types from a cleaned dictionary.
    Returns a dict mapping node paths to their types.
    Uses iterative stack-based approach to avoid recursion.
    """
    node_types = {}
    
    # Stack contains tuples of (current_data, current_path)
    stack = [(data, parent_path)]
    
    while stack:
        current_data, current_path = stack.pop()
        
        if isinstance(current_data, dict):
            for key, value in current_data.items():
                full_path = f"{current_path}.{key}" if current_path else key
                node_type = detect_value_type(value)
                node_types[full_path] = node_type
                
                # Check if this is a terminal node - stop traversal here
                if key in TERMINAL_NODES:
                    logger.debug(f"Terminal node reached: {full_path}, stopping traversal")
                    continue
                
                # Push complex types to stack (only if not terminal)
                if isinstance(value, (dict, list)):
                    stack.append((value, full_path))
        
        elif isinstance(current_data, list):
            # For lists, we track the list itself and its items
            if len(current_data) > 0:
                item_type = detect_value_type(current_data[0])
                node_types[f"{current_path}.__item__"] = item_type
                
                # Check parent key to see if we're inside a terminal node
                parent_key = current_path.split('.')[-1] if current_path else ""
                if parent_key not in TERMINAL_NODES:
                    if isinstance(current_data[0], (dict, list)):
                        stack.append((current_data[0], f"{current_path}.__item__"))
    
    return node_types


def build_relationship_graph_from_dict(data: Dict[str, Any], graph: nx.DiGraph, parent_path: str = ""):
    """
    Build a directed graph representing parent-child relationships in the JSON structure.
    Uses iterative stack-based approach.
    """
    # Stack contains tuples of (current_data, current_path)
    stack = [(data, parent_path)]
    
    while stack:
        current_data, current_path = stack.pop()
        
        if isinstance(current_data, dict):
            for key, value in current_data.items():
                child_path = f"{current_path}.{key}" if current_path else key
                
                # Add nodes first
                if current_path and current_path not in graph.nodes:
                    graph.add_node(current_path)
                
                if child_path not in graph.nodes:
                    graph.add_node(child_path)
                
                # Add edge from parent to child
                if current_path:
                    graph.add_edge(current_path, child_path)
                
                # Set node type
                node_type = detect_value_type(value)
                graph.nodes[child_path]['type'] = node_type
                
                # Check if this is a terminal node - stop traversal here
                if key in TERMINAL_NODES:
                    logger.debug(f"Terminal node reached in graph: {child_path}, stopping traversal")
                    continue
                
                # Push complex types to stack (only if not terminal)
                if isinstance(value, dict):
                    stack.append((value, child_path))
                elif isinstance(value, list) and len(value) > 0:
                    # For lists, add relationship to items
                    item_path = f"{child_path}.__item__"
                    
                    if item_path not in graph.nodes:
                        graph.add_node(item_path)
                    
                    graph.add_edge(child_path, item_path)
                    item_type = detect_value_type(value[0])
                    graph.nodes[item_path]['type'] = item_type
                    
                    # Check if parent is a terminal node
                    if key not in TERMINAL_NODES:
                        if isinstance(value[0], dict):
                            stack.append((value[0], item_path))
                        elif isinstance(value[0], list):
                            stack.append((value[0], item_path))


def remove_shortcuts_from_graph(graph: nx.DiGraph) -> nx.DiGraph:
    """
    Remove shortcut edges from the graph.
    A shortcut is an edge that bypasses intermediate nodes.
    We keep only the longest paths (remove transitive edges).
    """
    logger.info("Removing shortcuts from graph...")
    
    # Create a copy to modify
    optimized_graph = graph.copy()
    
    # Get all nodes
    nodes = list(graph.nodes())
    
    # For each pair of nodes, check if there's a direct edge
    # and if there's also a longer path between them
    edges_to_remove = []
    
    for source in nodes:
        for target in nodes:
            if source == target:
                continue
            
            # Check if there's a direct edge
            if not graph.has_edge(source, target):
                continue
            
            # Check if there's an alternative path (length > 1)
            try:
                # Find all simple paths from source to target
                paths = list(nx.all_simple_paths(graph, source, target))
                
                # If there are paths with length > 1, this is a shortcut
                has_longer_path = any(len(path) > 2 for path in paths)
                
                if has_longer_path:
                    edges_to_remove.append((source, target))
                    logger.debug(f"Removing shortcut edge: {source} -> {target}")
            
            except nx.NetworkXNoPath:
                continue
    
    # Remove the shortcut edges
    optimized_graph.remove_edges_from(edges_to_remove)
    
    logger.info(f"Removed {len(edges_to_remove)} shortcut edges")
    return optimized_graph


def reconstruct_schema_from_graph(graph: nx.DiGraph) -> SchemaNode:
    """
    Reconstruct the complete schema tree from the optimized graph.
    """
    logger.info("Reconstructing schema from graph...")
    
    # Find root nodes (nodes with no incoming edges)
    root_nodes = [node for node in graph.nodes() if graph.in_degree(node) == 0]
    
    if not root_nodes:
        raise ValueError("No root nodes found in graph")
    
    # Create root schema node
    root_schema = SchemaNode('root', 'dict')
    
    # Build tree from each root
    for root_node in root_nodes:
        # Stack contains tuples of (graph_node, schema_node)
        stack = [(root_node, root_schema)]
        
        while stack:
            graph_node, schema_node = stack.pop()
            
            # Get children from graph
            children = list(graph.successors(graph_node))
            
            for child in children:
                child_type = graph.nodes[child].get('type', 'unknown')
                child_name = child.split('.')[-1] if '.' in child else child
                
                # Add child to schema
                child_schema = schema_node.add_child(child_name, child_type)
                
                # Add to stack for further processing
                stack.append((child, child_schema))
    
    return root_schema


def build_graph_for_file(args):
    """Worker function to build graph for a single file."""
    file_path, cleaned_data = args
    file_graph = nx.DiGraph()
    build_relationship_graph_from_dict(cleaned_data, file_graph)
    return file_graph


def extract_and_queue_node_types(args):
    """
    Worker function to extract node types and put them in queues.
    Designed for multiprocessing.
    """
    file_path, cleaned_data = args
    
    # Extract node types
    node_types = extract_node_types_from_dict(cleaned_data)
    
    return (node_types, (file_path, cleaned_data))


def main():
    """Main execution function."""
    logger.info("Starting schema extraction pipeline...")
    
    # Get all JSON files
    json_files = glob.glob('test_json/*.json')
    logger.info(f"Found {len(json_files)} JSON files")
    
    if not json_files:
        logger.error("No JSON files found in test_json directory")
        return
    
    # Step 1: Clean JSON files using multiprocessing
    logger.info("Step 1: Cleaning JSON files...")
    manager = Manager()
    queue1 = manager.Queue()
    
    with Pool(processes=min(mp.cpu_count(), len(json_files))) as pool:
        results = pool.map(process_single_json_file, json_files)
    
    # Push cleaned data to queue1
    for file_path, cleaned_data in results:
        if cleaned_data is not None:
            queue1.put((file_path, cleaned_data))
    
    logger.info(f"Queue1 size after cleaning: {queue1.qsize()}")
    
    # Step 2: Extract node types using multiprocessing
    logger.info("Step 2: Extracting node types and building merged schema...")
    queue2 = manager.Queue()  # For node type dicts
    queue3 = manager.Queue()  # For original cleaned data
    
    # Prepare data for parallel processing
    queue1_items = []
    while not queue1.empty():
        queue1_items.append(queue1.get())
    
    # Verify queue1 is empty
    assert queue1.empty(), "Queue1 should be empty after reading all items"
    
    # Process in parallel using multiprocessing
    with Pool(processes=min(mp.cpu_count(), len(queue1_items))) as pool:
        parallel_results = pool.map(extract_and_queue_node_types, queue1_items)
    
    # Put results into queues
    for node_types, cleaned_item in parallel_results:
        queue2.put(node_types)
        queue3.put(cleaned_item)
    
    logger.info(f"Queue2 size: {queue2.qsize()}, Queue3 size: {queue3.qsize()}")
    
    # Merge all node type dictionaries
    logger.info("Merging node type dictionaries...")
    merged_node_types = {}
    while not queue2.empty():
        node_types = queue2.get()
        for path, node_type in node_types.items():
            if path in merged_node_types:
                # Merge types
                existing_type = merged_node_types[path]
                if existing_type != node_type:
                    merged_node_types[path] = f"{existing_type}|{node_type}"
            else:
                merged_node_types[path] = node_type
    
    logger.info(f"Merged {len(merged_node_types)} unique node paths")
    
    # Step 3: Build relationship graph using multiprocessing
    logger.info("Step 3: Building relationship graph...")
    
    # Prepare data for parallel processing
    queue3_items = []
    while not queue3.empty():
        queue3_items.append(queue3.get())
    
    # Verify queue3 is empty
    assert queue3.empty(), "Queue3 should be empty after reading all items"
    
    # Process in parallel
    with Pool(processes=min(mp.cpu_count(), len(queue3_items))) as pool:
        file_graphs = pool.map(build_graph_for_file, queue3_items)
    
    # Merge all graphs
    combined_graph = nx.DiGraph()
    for file_graph in file_graphs:
        combined_graph = nx.compose(combined_graph, file_graph)
    
    logger.info(f"Combined graph has {combined_graph.number_of_nodes()} nodes and {combined_graph.number_of_edges()} edges")
    
    # Save initial graph
    with open('graph_initial.pkl', 'wb') as f:
        pickle.dump(combined_graph, f)
    logger.info("Saved initial graph to graph_initial.pkl")
    
    # Step 4: Remove shortcuts
    logger.info("Step 4: Removing shortcuts from graph...")
    optimized_graph = remove_shortcuts_from_graph(combined_graph)
    
    # Save optimized graph
    with open('graph_optimized.pkl', 'wb') as f:
        pickle.dump(optimized_graph, f)
    logger.info("Saved optimized graph to graph_optimized.pkl")
    
    # Step 5: Reconstruct schema
    logger.info("Step 5: Reconstructing schema tree...")
    final_schema = reconstruct_schema_from_graph(optimized_graph)
    
    # Step 6: Save outputs
    logger.info("Step 6: Saving outputs...")
    
    # Save schema
    schema_dict = final_schema.to_dict()
    with open('test_json_schema.json', 'w', encoding='utf-8') as f:
        json.dump(schema_dict, f, indent=2, ensure_ascii=False)
    logger.info("Saved schema to test_json_schema.json")
    
    # Save node list
    node_list = {path: {'type': ntype} for path, ntype in merged_node_types.items()}
    with open('node_list.json', 'w', encoding='utf-8') as f:
        json.dump(node_list, f, indent=2, ensure_ascii=False)
    logger.info("Saved node list to node_list.json")
    
    # Save graphs in JSON format for readability
    graph_initial_json = nx.readwrite.json_graph.node_link_data(combined_graph)
    with open('graph_initial.json', 'w', encoding='utf-8') as f:
        json.dump(graph_initial_json, f, indent=2, ensure_ascii=False)
    
    graph_optimized_json = nx.readwrite.json_graph.node_link_data(optimized_graph)
    with open('graph_optimized.json', 'w', encoding='utf-8') as f:
        json.dump(graph_optimized_json, f, indent=2, ensure_ascii=False)
    
    logger.info("Schema extraction pipeline completed successfully!")
    logger.info(f"Final schema has {len(str(schema_dict))} characters")
    logger.info(f"Total unique node paths: {len(merged_node_types)}")


if __name__ == '__main__':
    main()
