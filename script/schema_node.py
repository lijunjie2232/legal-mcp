"""
SchemaNode class for representing nodes in the JSON schema tree.
Encapsulates node properties and methods for schema extraction.
"""

from typing import Dict, List, Optional, Any, Set
import json


class SchemaNode:
    """Represents a node in the JSON schema hierarchy."""
    
    def __init__(self, name: str, node_type: str = None):
        self.name = name
        self.node_type = node_type  # 'dict', 'list', 'str', 'int', 'bool', 'null'
        self.children: Dict[str, 'SchemaNode'] = {}
        self.parent: Optional['SchemaNode'] = None
        self.count = 0  # Number of times this node appears
        
    def add_child(self, child_name: str, child_type: str = None) -> 'SchemaNode':
        """Add a child node or return existing one."""
        if child_name not in self.children:
            child_node = SchemaNode(child_name, child_type)
            child_node.parent = self
            self.children[child_name] = child_node
        else:
            # Update type if not set
            if self.children[child_name].node_type is None and child_type is not None:
                self.children[child_name].node_type = child_type
        self.children[child_name].count += 1
        return self.children[child_name]
    
    def get_child(self, child_name: str) -> Optional['SchemaNode']:
        """Get a child node by name."""
        return self.children.get(child_name)
    
    def has_child(self, child_name: str) -> bool:
        """Check if node has a child with given name."""
        return child_name in self.children
    
    def equal(self, other: 'SchemaNode') -> bool:
        """Check if two nodes are equal (same name and type)."""
        if not isinstance(other, SchemaNode):
            return False
        return self.name == other.name and self.node_type == other.node_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        result = {
            'name': self.name,
            'type': self.node_type,
            'count': self.count
        }
        if self.children:
            result['children'] = {
                name: child.to_dict() 
                for name, child in self.children.items()
            }
        return result
    
    def __repr__(self) -> str:
        return f"SchemaNode(name='{self.name}', type='{self.node_type}', count={self.count})"
    
    def __eq__(self, other) -> bool:
        return self.equal(other)
    
    def __hash__(self):
        return hash((self.name, self.node_type))


def detect_value_type(value: Any) -> str:
    """Detect the type of a JSON value."""
    if value is None:
        return 'null'
    elif isinstance(value, bool):
        return 'bool'
    elif isinstance(value, int):
        return 'int'
    elif isinstance(value, float):
        return 'float'
    elif isinstance(value, str):
        return 'str'
    elif isinstance(value, dict):
        return 'dict'
    elif isinstance(value, list):
        return 'list'
    else:
        return 'unknown'


def build_schema_from_dict(data: Dict[str, Any], parent_node: SchemaNode = None) -> SchemaNode:
    """
    Build a schema tree from a dictionary using iterative stack-based approach.
    Avoids recursion to prevent stack overflow on large JSON files.
    """
    root = SchemaNode('root', 'dict')
    
    # Stack contains tuples of (current_data, current_node)
    stack = [(data, root)]
    
    while stack:
        current_data, current_node = stack.pop()
        
        if isinstance(current_data, dict):
            current_node.node_type = 'dict'
            for key, value in current_data.items():
                child_node = current_node.add_child(key)
                
                # Determine value type
                value_type = detect_value_type(value)
                child_node.node_type = value_type
                
                # If value is complex (dict or list), push to stack
                if isinstance(value, dict):
                    stack.append((value, child_node))
                elif isinstance(value, list):
                    # For lists, we need to analyze the items
                    if len(value) > 0:
                        # Create a special child for list items
                        item_node = child_node.add_child('__item__', detect_value_type(value[0]))
                        if isinstance(value[0], dict):
                            stack.append((value[0], item_node))
                        elif isinstance(value[0], list):
                            stack.append((value[0], item_node))
        elif isinstance(current_data, list):
            current_node.node_type = 'list'
            if len(current_data) > 0:
                item_type = detect_value_type(current_data[0])
                current_node.add_child('__item__', item_type)
                if isinstance(current_data[0], dict):
                    stack.append((current_data[0], current_node))
    
    return root


def merge_schema_nodes(node1: SchemaNode, node2: SchemaNode) -> SchemaNode:
    """
    Merge two schema nodes iteratively using stack-based approach.
    Combines children and updates counts.
    """
    # Stack contains tuples of (node1_subtree, node2_subtree, merged_subtree)
    stack = [(node1, node2, SchemaNode(node1.name, node1.node_type))]
    root_merged = stack[0][2]
    
    while stack:
        n1, n2, merged = stack.pop()
        
        # Update count
        merged.count = n1.count + n2.count
        
        # Merge types - prefer more specific type
        if n1.node_type and n2.node_type:
            if n1.node_type == n2.node_type:
                merged.node_type = n1.node_type
            elif n1.node_type == 'null':
                merged.node_type = n2.node_type
            elif n2.node_type == 'null':
                merged.node_type = n1.node_type
            else:
                # Keep both types as a union (store as string for now)
                merged.node_type = f"{n1.node_type}|{n2.node_type}"
        elif n1.node_type:
            merged.node_type = n1.node_type
        elif n2.node_type:
            merged.node_type = n2.node_type
        
        # Merge children from both nodes
        all_children = set(list(n1.children.keys()) + list(n2.children.keys()))
        for child_name in all_children:
            child1 = n1.get_child(child_name)
            child2 = n2.get_child(child_name)
            
            if child1 and child2:
                # Both have this child - merge recursively
                merged_child = merged.add_child(child_name)
                stack.append((child1, child2, merged_child))
            elif child1:
                # Only node1 has this child
                merged_child = SchemaNode(child_name, child1.node_type)
                merged_child.count = child1.count
                merged_child.parent = merged
                merged.children[child_name] = merged_child
                # Add grandchildren
                for grandchild_name, grandchild in child1.children.items():
                    stack.append((grandchild, SchemaNode(grandchild_name, grandchild.node_type), 
                                 merged_child.add_child(grandchild_name)))
            elif child2:
                # Only node2 has this child
                merged_child = SchemaNode(child_name, child2.node_type)
                merged_child.count = child2.count
                merged_child.parent = merged
                merged.children[child_name] = merged_child
                # Add grandchildren
                for grandchild_name, grandchild in child2.children.items():
                    stack.append((SchemaNode(grandchild_name, grandchild.node_type), grandchild,
                                 merged_child.add_child(grandchild_name)))
    
    return root_merged
