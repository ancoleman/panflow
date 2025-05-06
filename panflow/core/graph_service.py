"""
Graph Service module for PANFlow.

This module provides a centralized service for graph queries and operations,
making it easier to work with the graph database consistently across the application.
"""

from typing import Dict, List, Any, Optional, Union, Set
from lxml import etree

from .graph_utils import ConfigGraph
from .query_language import Query
from .query_engine import QueryExecutor

class GraphService:
    """Centralized service for graph queries and operations."""
    
    def __init__(self):
        self._graph_cache = {}  # Optional: Cache graphs by a suitable key
    
    def get_graph(self, tree: etree._ElementTree, refresh: bool = False) -> ConfigGraph:
        """
        Get or create a graph from the XML tree.
        
        Args:
            tree: ElementTree containing the configuration
            refresh: If True, rebuild the graph even if cached
            
        Returns:
            ConfigGraph object
        """
        # Optional: Implement caching based on a unique tree identifier
        # For now, always create a new graph
        graph = ConfigGraph()
        graph.build_from_xml(tree)
        return graph
    
    def find_objects_by_name_pattern(
        self, 
        tree: etree._ElementTree, 
        object_type: str, 
        pattern: str, 
        case_sensitive: bool = False
    ) -> List[str]:
        """
        Find objects by name pattern.
        
        Args:
            tree: ElementTree containing the configuration
            object_type: Type of object to find (address, service, etc.)
            pattern: Regex pattern to match object names
            case_sensitive: Whether to use case-sensitive matching
            
        Returns:
            List of object names matching the pattern
        """
        graph = self.get_graph(tree)
        
        # Implement case sensitivity
        case_modifier = "" if case_sensitive else "(?i)"
        
        query_text = f"MATCH (a:{object_type}) WHERE a.name =~ '{case_modifier}{pattern}' RETURN a.name"
        return self._execute_name_query(graph, query_text)
    
    def find_objects_by_value_pattern(
        self, 
        tree: etree._ElementTree, 
        object_type: str, 
        pattern: str,
        wildcard_support: bool = True,
        case_sensitive: bool = False
    ) -> List[str]:
        """
        Find objects by value pattern.
        
        Args:
            tree: ElementTree containing the configuration
            object_type: Type of object to find (address, service, etc.)
            pattern: Pattern to match object values (can use * as wildcards if wildcard_support=True)
            wildcard_support: Whether to treat * as wildcards
            case_sensitive: Whether to use case-sensitive matching
            
        Returns:
            List of object names with values matching the pattern
        """
        graph = self.get_graph(tree)
        
        # Process wildcards if supported
        if wildcard_support:
            pattern = pattern.replace(".", "\\.").replace("*", ".*")
        
        # Implement case sensitivity
        case_modifier = "" if case_sensitive else "(?i)"
        
        query_text = f"MATCH (a:{object_type}) WHERE a.value =~ '{case_modifier}.*{pattern}.*' RETURN a.name"
        return self._execute_name_query(graph, query_text)
    
    def find_address_objects_containing_ip(
        self, 
        tree: etree._ElementTree, 
        ip_fragment: str
    ) -> List[str]:
        """
        Find address objects containing a specific IP or subnet.
        
        Args:
            tree: ElementTree containing the configuration
            ip_fragment: IP fragment to search for
            
        Returns:
            List of address object names containing the IP fragment
        """
        graph = self.get_graph(tree)
        
        # Escape dots for regex
        ip_pattern = ip_fragment.replace(".", "\\.")
        
        query_text = f"MATCH (a:address) WHERE a.value =~ '.*{ip_pattern}.*' RETURN a.name"
        return self._execute_name_query(graph, query_text)
    
    def find_service_objects_with_port(
        self, 
        tree: etree._ElementTree, 
        port: str
    ) -> List[str]:
        """
        Find service objects with a specific port.
        
        Args:
            tree: ElementTree containing the configuration
            port: Port to search for
            
        Returns:
            List of service object names with the specified port
        """
        graph = self.get_graph(tree)
        
        query_text = f"MATCH (s:service) WHERE s.dst_port == '{port}' RETURN s.name"
        return self._execute_name_query(graph, query_text)
    
    def find_unused_objects(
        self, 
        tree: etree._ElementTree, 
        object_type: str
    ) -> List[str]:
        """
        Find objects that are not referenced by any policy or group.
        
        Args:
            tree: ElementTree containing the configuration
            object_type: Type of object to find (address, service, etc.)
            
        Returns:
            List of unused object names
        """
        graph = self.get_graph(tree)
        
        query_text = f"""
        MATCH (a:{object_type}) 
        WHERE NOT (()-[:uses-source|uses-destination|contains]->(a)) 
        RETURN a.name
        """
        return self._execute_name_query(graph, query_text)
    
    def execute_custom_query(
        self, 
        tree: etree._ElementTree, 
        query_text: str
    ) -> List[Dict[str, Any]]:
        """
        Execute a custom graph query.
        
        Args:
            tree: ElementTree containing the configuration
            query_text: Custom graph query to execute
            
        Returns:
            List of result rows
        """
        graph = self.get_graph(tree)
        
        # Ensure the query has a RETURN clause
        if "RETURN" not in query_text.upper():
            raise ValueError("Query must include a RETURN clause")
        
        query = Query(query_text)
        executor = QueryExecutor(graph)
        return executor.execute(query)
    
    def filter_objects_by_query(
        self, 
        tree: etree._ElementTree,
        objects: List[Any],
        object_type: str,
        query_text: str,
        name_attribute: str = "object_name"
    ) -> List[Any]:
        """
        Filter a list of objects using a graph query.
        
        Args:
            tree: ElementTree containing the configuration
            objects: List of objects to filter
            object_type: Type of object in the graph
            query_text: Graph query to filter objects
            name_attribute: Attribute name on objects containing the object name
            
        Returns:
            Filtered list of objects
        """
        # Get names of objects matching the query
        graph = self.get_graph(tree)
        
        # Ensure the query returns object names
        if "RETURN" not in query_text.upper():
            query_text = f"{query_text} RETURN a.name"
        
        matching_names = self._execute_name_query(graph, query_text)
        
        # Filter objects by name
        return [obj for obj in objects if getattr(obj, name_attribute, None) in matching_names]
    
    def _execute_name_query(self, graph: ConfigGraph, query_text: str) -> List[str]:
        """
        Execute a query and extract object names from the results.
        
        Args:
            graph: ConfigGraph to query
            query_text: Query text to execute
            
        Returns:
            List of object names from the query results
        """
        query = Query(query_text)
        executor = QueryExecutor(graph)
        results = executor.execute(query)
        
        # Extract names from results
        names = []
        for row in results:
            for key, value in row.items():
                if key.endswith(".name"):
                    names.append(value)
                elif len(row) == 1:  # If only one column, assume it's the name
                    names.append(list(row.values())[0])
                    break
        
        return names