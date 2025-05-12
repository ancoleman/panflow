"""
Query execution engine for the graph query language.

This module implements the execution engine for the graph query language
defined in the query_language module.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
import networkx as nx

from panflow.core.query_language import (
    Query,
    MatchNode,
    WhereNode,
    ReturnNode,
    PatternNode,
    EntityNode,
    RelationshipNode,
    ExpressionNode,
    BinaryOpNode,
    UnaryOpNode,
    PropertyAccessNode,
    LiteralNode,
)

# Set up logging
logger = logging.getLogger(__name__)


class QueryContext:
    """
    Context for query execution.

    This class holds the state of the query execution including variable bindings.
    """

    def __init__(self, graph):
        """
        Initialize a new query context.

        Args:
            graph: The graph to query
        """
        self.graph = graph
        self.bindings = {}

    def bind(self, variable: str, value: Any):
        """
        Bind a value to a variable.

        Args:
            variable: The variable name
            value: The value to bind
        """
        self.bindings[variable] = value

    def get_binding(self, variable: str) -> Any:
        """
        Get the value bound to a variable.

        Args:
            variable: The variable name

        Returns:
            The bound value
        """
        if variable not in self.bindings:
            raise ValueError(f"Variable '{variable}' is not bound")
        return self.bindings[variable]


class QueryExecutor:
    """
    Executor for graph queries.

    This class executes queries on the graph and returns the results.
    """

    def __init__(self, graph):
        """
        Initialize a new query executor.

        Args:
            graph: The graph to query
        """
        self.graph = graph

    def execute(self, query: Query) -> List[Dict[str, Any]]:
        """
        Execute a query on the graph.

        Args:
            query: The query to execute

        Returns:
            List of result records
        """
        if not query.match_nodes:
            raise ValueError("Query must have at least one MATCH clause")

        if not query.return_nodes:
            raise ValueError("Query must have a RETURN clause")

        # Start with an empty binding
        contexts = [QueryContext(self.graph)]

        # Execute MATCH clauses
        for match_node in query.match_nodes:
            contexts = self._execute_match(match_node, contexts)

        # Execute WHERE clauses
        for where_node in query.where_nodes:
            contexts = self._execute_where(where_node, contexts)

        # Execute RETURN clauses
        results = []
        for return_node in query.return_nodes:
            results.extend(self._execute_return(return_node, contexts))

        return results

    def _execute_match(
        self, match_node: MatchNode, contexts: List[QueryContext]
    ) -> List[QueryContext]:
        """
        Execute a MATCH clause.

        Args:
            match_node: The MATCH clause AST node
            contexts: List of query contexts

        Returns:
            List of updated query contexts
        """
        new_contexts = []

        for context in contexts:
            # For each pattern in the MATCH clause
            for pattern in match_node.patterns:
                pattern_contexts = self._execute_pattern(pattern, [context])
                new_contexts.extend(pattern_contexts)

        return new_contexts

    def _execute_pattern(
        self, pattern: PatternNode, contexts: List[QueryContext]
    ) -> List[QueryContext]:
        """
        Execute a pattern in a MATCH clause.

        Args:
            pattern: The pattern AST node
            contexts: List of query contexts

        Returns:
            List of updated query contexts
        """
        if not pattern.entities:
            return contexts

        new_contexts = []

        for context in contexts:
            # Start with the first entity
            entity_contexts = self._execute_entity(pattern.entities[0], [context])

            # For each relationship and subsequent entity
            for i, relationship in enumerate(pattern.relationships):
                entity = pattern.entities[i + 1]

                # For each context from the previous step
                next_contexts = []
                for entity_context in entity_contexts:
                    # Execute the relationship and target entity
                    rel_contexts = self._execute_relationship(
                        relationship, entity, [entity_context]
                    )
                    next_contexts.extend(rel_contexts)

                entity_contexts = next_contexts

            new_contexts.extend(entity_contexts)

        return new_contexts

    def _execute_entity(
        self, entity: EntityNode, contexts: List[QueryContext]
    ) -> List[QueryContext]:
        """
        Execute an entity pattern.

        Args:
            entity: The entity AST node
            contexts: List of query contexts

        Returns:
            List of updated query contexts
        """
        if not entity.labels:
            raise ValueError("Entity must have at least one label")

        new_contexts = []

        for context in contexts:
            # Find nodes in the graph that match the entity pattern
            matches = self._find_matching_nodes(entity, context)

            # For each matching node, create a new context
            for node_id, node_data in matches:
                # Create a new context with the entity variable bound to the node
                new_context = QueryContext(context.graph)
                new_context.bindings = context.bindings.copy()

                if entity.variable is not None:
                    # Bind the entity to the variable
                    new_context.bind(entity.variable, node_id)

                new_contexts.append(new_context)

        return new_contexts

    def _execute_relationship(
        self,
        relationship: RelationshipNode,
        target_entity: EntityNode,
        contexts: List[QueryContext],
    ) -> List[QueryContext]:
        """
        Execute a relationship pattern.

        Args:
            relationship: The relationship AST node
            target_entity: The target entity AST node
            contexts: List of query contexts

        Returns:
            List of updated query contexts
        """
        new_contexts = []

        for context in contexts:
            # Get the source entity ID (last entity before this relationship)
            source_id = None
            for var, value in context.bindings.items():
                if isinstance(value, str) and ":" in value:
                    # This looks like a node ID
                    source_id = value

            if not source_id:
                continue

            # Find nodes connected to the source node
            matches = self._find_connected_nodes(source_id, relationship, target_entity, context)

            # For each matching node, create a new context
            for edge_id, target_id, target_data in matches:
                # Create a new context with the target entity and relationship bound
                new_context = QueryContext(context.graph)
                new_context.bindings = context.bindings.copy()

                if target_entity.variable is not None:
                    # Bind the target entity to its variable
                    new_context.bind(target_entity.variable, target_id)

                if relationship.variable is not None:
                    # Bind the relationship to its variable
                    new_context.bind(relationship.variable, edge_id)

                new_contexts.append(new_context)

        return new_contexts

    def _find_matching_nodes(
        self, entity: EntityNode, context: QueryContext
    ) -> List[Tuple[str, Dict]]:
        """
        Find nodes in the graph that match the entity pattern.

        Args:
            entity: The entity AST node
            context: Query context

        Returns:
            List of (node_id, node_data) tuples for matching nodes
        """
        matches = []

        # For all nodes in the graph
        for node_id, node_data in context.graph.graph.nodes(data=True):
            # Skip the root node
            if node_id == context.graph.root_node:
                continue

            # Check if the node matches the entity pattern
            if self._node_matches_entity(node_id, node_data, entity):
                matches.append((node_id, node_data))

        return matches

    def _node_matches_entity(self, node_id: str, node_data: Dict, entity: EntityNode) -> bool:
        """
        Check if a node matches an entity pattern.

        Args:
            node_id: ID of the node
            node_data: Data of the node
            entity: The entity AST node

        Returns:
            True if the node matches the entity pattern, False otherwise
        """
        # Check node type against entity label
        node_type = node_data.get("type", "")

        # Print debug info
        logger.debug(
            f"Matching node {node_id} with type {node_type} against entity with labels {entity.labels}"
        )

        # Check if any of the entity labels match the node type
        if not any(label.lower() == node_type.lower() for label in entity.labels):
            # Try alternate check: if the node_id contains the label
            node_type_from_id = node_id.split(":")[0] if ":" in node_id else ""
            if not any(label.lower() == node_type_from_id.lower() for label in entity.labels):
                return False

        # Check properties
        for prop_name, prop_value in entity.properties.items():
            if prop_name not in node_data or node_data[prop_name] != prop_value:
                return False

        return True

    def _find_connected_nodes(
        self,
        source_id: str,
        relationship: RelationshipNode,
        target_entity: EntityNode,
        context: QueryContext,
    ) -> List[Tuple[str, str, Dict]]:
        """
        Find nodes connected to a source node by a relationship that match a target entity pattern.

        Args:
            source_id: ID of the source node
            relationship: The relationship AST node
            target_entity: The target entity AST node
            context: Query context

        Returns:
            List of (edge_id, target_id, target_data) tuples for matching connected nodes
        """
        matches = []

        # Determine relationship direction
        if relationship.direction == "->":
            # Outgoing edges
            for target_id in context.graph.graph.successors(source_id):
                edge_data = context.graph.graph.get_edge_data(source_id, target_id)
                edge_id = f"{source_id}_to_{target_id}"

                # Check if the relationship matches
                if self._relationship_matches(edge_data, relationship):
                    # Check if the target node matches the target entity
                    target_data = context.graph.graph.nodes[target_id]
                    if self._node_matches_entity(target_id, target_data, target_entity):
                        matches.append((edge_id, target_id, target_data))

        elif relationship.direction == "<-":
            # Incoming edges
            for target_id in context.graph.graph.predecessors(source_id):
                edge_data = context.graph.graph.get_edge_data(target_id, source_id)
                edge_id = f"{target_id}_to_{source_id}"

                # Check if the relationship matches
                if self._relationship_matches(edge_data, relationship):
                    # Check if the target node matches the target entity
                    target_data = context.graph.graph.nodes[target_id]
                    if self._node_matches_entity(target_id, target_data, target_entity):
                        matches.append((edge_id, target_id, target_data))

        else:
            # Both directions
            # First check outgoing edges
            for target_id in context.graph.graph.successors(source_id):
                edge_data = context.graph.graph.get_edge_data(source_id, target_id)
                edge_id = f"{source_id}_to_{target_id}"

                # Check if the relationship matches
                if self._relationship_matches(edge_data, relationship):
                    # Check if the target node matches the target entity
                    target_data = context.graph.graph.nodes[target_id]
                    if self._node_matches_entity(target_id, target_data, target_entity):
                        matches.append((edge_id, target_id, target_data))

            # Then check incoming edges
            for target_id in context.graph.graph.predecessors(source_id):
                edge_data = context.graph.graph.get_edge_data(target_id, source_id)
                edge_id = f"{target_id}_to_{source_id}"

                # Check if the relationship matches
                if self._relationship_matches(edge_data, relationship):
                    # Check if the target node matches the target entity
                    target_data = context.graph.graph.nodes[target_id]
                    if self._node_matches_entity(target_id, target_data, target_entity):
                        matches.append((edge_id, target_id, target_data))

        return matches

    def _relationship_matches(self, edge_data: Dict, relationship: RelationshipNode) -> bool:
        """
        Check if an edge matches a relationship pattern.

        Args:
            edge_data: Data of the edge
            relationship: The relationship AST node

        Returns:
            True if the edge matches the relationship pattern, False otherwise
        """
        if not relationship.types:
            return True

        # Check relationship type
        relation = edge_data.get("relation", "")

        # Check if any of the relationship types match the edge relation
        if not any(rel_type.lower() == relation.lower() for rel_type in relationship.types):
            return False

        # Check properties
        for prop_name, prop_value in relationship.properties.items():
            if prop_name not in edge_data or edge_data[prop_name] != prop_value:
                return False

        return True

    def _execute_where(
        self, where_node: WhereNode, contexts: List[QueryContext]
    ) -> List[QueryContext]:
        """
        Execute a WHERE clause.

        Args:
            where_node: The WHERE clause AST node
            contexts: List of query contexts

        Returns:
            List of filtered query contexts
        """
        result_contexts = []

        for context in contexts:
            # Evaluate the WHERE expression
            if self._evaluate_expression(where_node.expression, context):
                result_contexts.append(context)

        return result_contexts

    def _evaluate_expression(self, expression: ExpressionNode, context: QueryContext) -> bool:
        """
        Evaluate an expression in a WHERE clause.

        Args:
            expression: The expression AST node
            context: Query context

        Returns:
            Result of the expression evaluation
        """
        if isinstance(expression, BinaryOpNode):
            left_value = self._evaluate_expression(expression.left, context)
            right_value = self._evaluate_expression(expression.right, context)

            if expression.operator == "AND":
                return left_value and right_value
            elif expression.operator == "OR":
                return left_value or right_value
            elif expression.operator == "==":
                return left_value == right_value
            elif expression.operator == "!=":
                return left_value != right_value
            elif expression.operator == ">":
                return left_value > right_value
            elif expression.operator == ">=":
                return left_value >= right_value
            elif expression.operator == "<":
                return left_value < right_value
            elif expression.operator == "<=":
                return left_value <= right_value
            elif expression.operator == "=~":
                # Regex match
                if not isinstance(left_value, str) or not isinstance(right_value, str):
                    return False
                return bool(re.search(right_value, left_value))

        elif isinstance(expression, UnaryOpNode):
            operand_value = self._evaluate_expression(expression.operand, context)

            if expression.operator == "NOT":
                return not operand_value

        elif isinstance(expression, PropertyAccessNode):
            variable = expression.variable
            property_name = expression.property_name

            # Get the node ID from the variable binding
            node_id = context.get_binding(variable)

            # Get the node data
            node_data = context.graph.graph.nodes[node_id]

            # Return the property value
            return node_data.get(property_name)

        elif isinstance(expression, LiteralNode):
            return expression.value

        raise ValueError(f"Unsupported expression type: {type(expression)}")

    def _execute_return(
        self, return_node: ReturnNode, contexts: List[QueryContext]
    ) -> List[Dict[str, Any]]:
        """
        Execute a RETURN clause.

        Args:
            return_node: The RETURN clause AST node
            contexts: List of query contexts

        Returns:
            List of result records
        """
        results = []

        for context in contexts:
            record = {}

            # For each return item
            for expr, alias in return_node.items:
                # Evaluate the expression
                value = self._evaluate_return_expression(expr, context)

                # Determine the key for the result record
                key = alias if alias else self._expression_to_key(expr)

                # Add to the record
                record[key] = value

            results.append(record)

        return results

    def _evaluate_return_expression(self, expression: ExpressionNode, context: QueryContext) -> Any:
        """
        Evaluate an expression in a RETURN clause.

        Args:
            expression: The expression AST node
            context: Query context

        Returns:
            Result of the expression evaluation
        """
        if isinstance(expression, PropertyAccessNode):
            variable = expression.variable
            property_name = expression.property_name

            # Get the node ID from the variable binding
            node_id = context.get_binding(variable)

            # If property is 'id', return the node ID
            if property_name == "id":
                return node_id

            # Get the node data
            node_data = context.graph.graph.nodes[node_id]

            # If property is 'edges', return the edges
            if property_name == "edges_out":
                edges = []
                for succ in context.graph.graph.successors(node_id):
                    edge_data = context.graph.graph.get_edge_data(node_id, succ)
                    edge_type = edge_data.get("relation", "unknown")
                    edges.append({"target": succ, "type": edge_type})
                return edges

            if property_name == "edges_in":
                edges = []
                for pred in context.graph.graph.predecessors(node_id):
                    edge_data = context.graph.graph.get_edge_data(pred, node_id)
                    edge_type = edge_data.get("relation", "unknown")
                    edges.append({"source": pred, "type": edge_type})
                return edges

            # Return the property value
            return node_data.get(property_name)

        elif isinstance(expression, LiteralNode):
            return expression.value

        # Variable reference (return the entire node)
        elif isinstance(expression, str):
            variable = expression

            # Get the node ID from the variable binding
            node_id = context.get_binding(variable)

            # Get the node data
            node_data = context.graph.graph.nodes[node_id]

            # Return a copy of the node data without the XML element
            result = dict(node_data)
            if "xml" in result:
                del result["xml"]

            return result

        raise ValueError(f"Unsupported expression type: {type(expression)}")

    def _expression_to_key(self, expression: ExpressionNode) -> str:
        """
        Convert an expression to a key string for result records.

        Args:
            expression: The expression AST node

        Returns:
            String key for the result record
        """
        if isinstance(expression, PropertyAccessNode):
            return f"{expression.variable}.{expression.property_name}"

        elif isinstance(expression, str):
            return expression

        return str(expression)
