"""
Graph query language for PAN-OS configurations.

This module provides a simple query language for querying the graph representation
of PAN-OS configurations.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from enum import Enum

# Set up logging
logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Token types for the query language lexer."""
    IDENTIFIER = "IDENTIFIER"       # Node types, property names
    STRING = "STRING"               # String literals
    NUMBER = "NUMBER"               # Numeric literals
    DOT = "DOT"                     # . (property access)
    COLON = "COLON"                 # : (type specifier)
    LPAREN = "LPAREN"               # (
    RPAREN = "RPAREN"               # )
    LBRACKET = "LBRACKET"           # [
    RBRACKET = "RBRACKET"           # ]
    COMMA = "COMMA"                 # ,
    ARROW = "ARROW"                 # -> (relationship)
    REVERSE_ARROW = "REVERSE_ARROW" # <- (reverse relationship)
    OPERATOR = "OPERATOR"           # ==, !=, >, <, >=, <=, etc.
    LOGICAL = "LOGICAL"             # AND, OR, NOT
    WHERE = "WHERE"                 # WHERE keyword
    WITH = "WITH"                   # WITH keyword
    MATCH = "MATCH"                 # MATCH keyword
    RETURN = "RETURN"               # RETURN keyword
    WHITESPACE = "WHITESPACE"       # Spaces, tabs, newlines
    EOF = "EOF"                     # End of input


class Token:
    """Represents a token in the query language."""
    
    def __init__(self, token_type: TokenType, value: str, position: int):
        """
        Initialize a new token.
        
        Args:
            token_type: The type of the token
            value: The string value of the token
            position: The position in the input string
        """
        self.type = token_type
        self.value = value
        self.position = position
        
    def __repr__(self):
        return f"Token({self.type}, '{self.value}', pos={self.position})"


class Lexer:
    """
    Lexer for the query language.
    
    This class tokenizes the input string according to the query language grammar.
    """
    
    # Token patterns
    TOKEN_PATTERNS = [
        (r'[ \t\n\r]+', TokenType.WHITESPACE),
        (r'MATCH', TokenType.MATCH),
        (r'WHERE', TokenType.WHERE),
        (r'WITH', TokenType.WITH),
        (r'RETURN', TokenType.RETURN),
        (r'AND', TokenType.LOGICAL),
        (r'OR', TokenType.LOGICAL),
        (r'NOT', TokenType.LOGICAL),
        (r'-\[:.*?\]->', None),  # Special pattern for relationship with type
        (r'->', TokenType.ARROW),
        (r'<-', TokenType.REVERSE_ARROW),
        (r'-\[', None),  # Special pattern for start of relationship
        (r'\]->', None),  # Special pattern for end of relationship with arrow
        (r'\]-', None),  # Special pattern for end of relationship
        (r'\.', TokenType.DOT),
        (r':', TokenType.COLON),
        (r',', TokenType.COMMA),
        (r'\(', TokenType.LPAREN),
        (r'\)', TokenType.RPAREN),
        (r'\[', TokenType.LBRACKET),
        (r'\]', TokenType.RBRACKET),
        (r'==|!=|>=|<=|>|<|=~', TokenType.OPERATOR),
        (r'"[^"]*"', TokenType.STRING),
        (r"'[^']*'", TokenType.STRING),
        (r'-?\d+(\.\d+)?', TokenType.NUMBER),
        (r'[a-zA-Z_][a-zA-Z0-9_-]*', TokenType.IDENTIFIER),  # Note: hyphen is not escaped now
    ]
    
    def __init__(self, input_string: str):
        """
        Initialize the lexer with an input string.
        
        Args:
            input_string: The query string to tokenize
        """
        self.input = input_string
        self.position = 0
        self.tokens = []
        
    def tokenize(self) -> List[Token]:
        """
        Tokenize the input string.
        
        Returns:
            List of tokens
        """
        self.tokens = []
        
        while self.position < len(self.input):
            self._tokenize_next()
            
        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, "", self.position))
        
        # Filter out whitespace tokens
        return [t for t in self.tokens if t.type != TokenType.WHITESPACE]
        
    def _tokenize_next(self):
        """Tokenize the next token in the input."""
        for pattern, token_type in self.TOKEN_PATTERNS:
            match = re.match(pattern, self.input[self.position:])
            if match:
                value = match.group(0)
                token = Token(token_type, value, self.position)
                
                # Handle special case for '->' and '<-' arrows
                if token_type == TokenType.IDENTIFIER and (value == '-' or value == '<-' or value == '->'):
                    if value == '->':
                        token = Token(TokenType.ARROW, value, self.position)
                    elif value == '<-':
                        token = Token(TokenType.REVERSE_ARROW, value, self.position)
                
                self.tokens.append(token)
                self.position += len(value)
                return
                
        # If we get here, we couldn't match the input
        invalid_char = self.input[self.position]
        raise ValueError(f"Invalid character '{invalid_char}' at position {self.position}")


class QueryNode:
    """Base class for all query AST nodes."""
    pass


class MatchNode(QueryNode):
    """AST node for MATCH clause."""
    
    def __init__(self, patterns: List['PatternNode']):
        """
        Initialize a new MATCH node.
        
        Args:
            patterns: List of pattern nodes
        """
        self.patterns = patterns


class PatternNode(QueryNode):
    """AST node for a pattern in a MATCH clause."""
    
    def __init__(self, entities: List['EntityNode'], relationships: List['RelationshipNode']):
        """
        Initialize a new pattern node.
        
        Args:
            entities: List of entity nodes in the pattern
            relationships: List of relationship nodes in the pattern
        """
        self.entities = entities
        self.relationships = relationships


class EntityNode(QueryNode):
    """AST node for an entity in a pattern."""
    
    def __init__(self, variable: Optional[str], labels: List[str], properties: Dict[str, Any]):
        """
        Initialize a new entity node.
        
        Args:
            variable: Optional variable name for this entity
            labels: List of labels for this entity (e.g., "address", "service")
            properties: Properties for this entity
        """
        self.variable = variable
        self.labels = labels
        self.properties = properties
        
    def __repr__(self):
        return f"EntityNode(variable={self.variable}, labels={self.labels}, properties={self.properties})"


class RelationshipNode(QueryNode):
    """AST node for a relationship in a pattern."""
    
    def __init__(self, variable: Optional[str], types: List[str], 
                 properties: Dict[str, Any], direction: str):
        """
        Initialize a new relationship node.
        
        Args:
            variable: Optional variable name for this relationship
            types: List of relationship types
            properties: Properties for this relationship
            direction: Direction of the relationship ('->', '<-', or '-')
        """
        self.variable = variable
        self.types = types
        self.properties = properties
        self.direction = direction


class WhereNode(QueryNode):
    """AST node for WHERE clause."""
    
    def __init__(self, expression: 'ExpressionNode'):
        """
        Initialize a new WHERE node.
        
        Args:
            expression: The filter expression
        """
        self.expression = expression


class ExpressionNode(QueryNode):
    """Base class for expression AST nodes."""
    pass


class BinaryOpNode(ExpressionNode):
    """AST node for binary operations."""
    
    def __init__(self, left: ExpressionNode, operator: str, right: ExpressionNode):
        """
        Initialize a new binary operation node.
        
        Args:
            left: Left operand
            operator: Operator string
            right: Right operand
        """
        self.left = left
        self.operator = operator
        self.right = right


class UnaryOpNode(ExpressionNode):
    """AST node for unary operations."""
    
    def __init__(self, operator: str, operand: ExpressionNode):
        """
        Initialize a new unary operation node.
        
        Args:
            operator: Operator string
            operand: The operand
        """
        self.operator = operator
        self.operand = operand


class PropertyAccessNode(ExpressionNode):
    """AST node for property access."""
    
    def __init__(self, variable: str, property_name: str):
        """
        Initialize a new property access node.
        
        Args:
            variable: Variable name
            property_name: Property name
        """
        self.variable = variable
        self.property_name = property_name


class LiteralNode(ExpressionNode):
    """AST node for literal values."""
    
    def __init__(self, value: Any, value_type: str):
        """
        Initialize a new literal node.
        
        Args:
            value: The literal value
            value_type: Type of the value ("string", "number", "boolean", etc.)
        """
        self.value = value
        self.value_type = value_type


class ReturnNode(QueryNode):
    """AST node for RETURN clause."""
    
    def __init__(self, items: List[Tuple[ExpressionNode, Optional[str]]]):
        """
        Initialize a new RETURN node.
        
        Args:
            items: List of (expression, alias) tuples for the return items
        """
        self.items = items


class QueryParser:
    """
    Parser for the query language.
    
    This class parses tokens from the lexer into an abstract syntax tree (AST).
    """
    
    def __init__(self, lexer: Lexer):
        """
        Initialize the parser with a lexer.
        
        Args:
            lexer: Lexer for tokenizing the input
        """
        self.lexer = lexer
        self.tokens = []
        self.current = 0
        
    def parse(self) -> List[QueryNode]:
        """
        Parse the input into an AST.
        
        Returns:
            List of query nodes representing the AST
        """
        self.tokens = self.lexer.tokenize()
        self.current = 0
        
        # Parse the query
        nodes = []
        
        while not self._is_at_end():
            # For now, we only support simple MATCH ... WHERE ... RETURN queries
            if self._check(TokenType.MATCH):
                nodes.append(self._parse_match_clause())
            elif self._check(TokenType.WHERE):
                nodes.append(self._parse_where_clause())
            elif self._check(TokenType.RETURN):
                nodes.append(self._parse_return_clause())
            else:
                raise ValueError(f"Unexpected token {self._peek()} at position {self._peek().position}")
                
        return nodes
        
    def _parse_match_clause(self) -> MatchNode:
        """Parse a MATCH clause."""
        self._consume(TokenType.MATCH, "Expected 'MATCH' keyword")
        
        patterns = []
        
        # Parse one or more patterns separated by commas
        patterns.append(self._parse_pattern())
        
        while self._match(TokenType.COMMA):
            patterns.append(self._parse_pattern())
            
        return MatchNode(patterns)
        
    def _parse_pattern(self) -> PatternNode:
        """Parse a pattern in a MATCH clause."""
        entities = []
        relationships = []
        
        # Ensure we have an opening parenthesis for the first entity
        self._consume(TokenType.LPAREN, "Expected '(' to start pattern")
        
        # Parse the first entity
        entities.append(self._parse_entity())
        
        # Parse any relationships and further entities
        while (self._check(TokenType.IDENTIFIER) and 
              self._peek().value == '-' and 
              self._peek_next().type == TokenType.LBRACKET) or self._check(TokenType.ARROW) or self._check(TokenType.REVERSE_ARROW):
            
            # Handle the relationship format: -[:type]->
            if self._check(TokenType.IDENTIFIER) and self._peek().value == '-':
                self._advance()  # Consume '-'
                relationship = self._parse_relationship_type()
                # Look for -> or -
                if self._match(TokenType.ARROW):
                    direction = "->"
                else:
                    self._consume(TokenType.IDENTIFIER, "Expected '-' or '->'")
                    direction = "-"
            elif self._match(TokenType.ARROW):
                direction = "->"
                relationship = self._parse_relationship(direction)
            elif self._match(TokenType.REVERSE_ARROW):
                direction = "<-"
                relationship = self._parse_relationship(direction)
            else:
                raise ValueError(f"Expected relationship at {self._peek().position}")
                
            relationships.append(relationship)
            
            # Ensure we have an opening parenthesis for the next entity
            self._consume(TokenType.LPAREN, "Expected '(' for next entity")
            
            # Parse the next entity
            entities.append(self._parse_entity())
            
        return PatternNode(entities, relationships)
        
    def _parse_relationship_type(self) -> RelationshipNode:
        """Parse a relationship type."""
        variable = None
        types = []
        properties = {}
        
        # Parse the relationship type in brackets: [:type]
        self._consume(TokenType.LBRACKET, "Expected '['")
        self._consume(TokenType.COLON, "Expected ':'")
        
        # Parse the relationship type
        type_name = self._consume(TokenType.IDENTIFIER, "Expected relationship type").value
        types.append(type_name)
        
        # Parse optional properties
        if self._match(TokenType.LBRACKET):
            properties = self._parse_properties()
            self._consume(TokenType.RBRACKET, "Expected ']'")
                
        self._consume(TokenType.RBRACKET, "Expected ']'")
        
        return RelationshipNode(variable, types, properties, "->")
        
    def _parse_entity(self) -> EntityNode:
        """Parse an entity in a pattern."""
        variable = None
        labels = []
        properties = {}
        
        # Parse opening parenthesis (already consumed in _parse_pattern)
        
        # Parse optional variable name
        if self._check(TokenType.IDENTIFIER) and self._peek_next().type == TokenType.COLON:
            variable = self._consume(TokenType.IDENTIFIER, "Expected identifier").value
            self._consume(TokenType.COLON, "Expected ':'")
            
        # Parse one or more labels
        label = self._consume(TokenType.IDENTIFIER, "Expected label").value
        labels.append(label)
        
        # Parse optional properties
        if self._match(TokenType.LBRACKET):
            properties = self._parse_properties()
            self._consume(TokenType.RBRACKET, "Expected ']'")
            
        # Parse closing parenthesis
        self._consume(TokenType.RPAREN, "Expected ')'")
            
        return EntityNode(variable, labels, properties)
        
    def _parse_relationship(self, direction: str) -> RelationshipNode:
        """Parse a relationship in a pattern."""
        variable = None
        types = []
        properties = {}
        
        # Parse optional variable and type information in brackets
        if self._match(TokenType.LBRACKET):
            # Parse optional variable name
            if self._check(TokenType.IDENTIFIER) and self._peek_next().type == TokenType.COLON:
                variable = self._consume(TokenType.IDENTIFIER, "Expected identifier").value
                self._consume(TokenType.COLON, "Expected ':'")
                
            # Parse relationship type
            type_name = self._consume(TokenType.IDENTIFIER, "Expected relationship type").value
            types.append(type_name)
            
            # Parse optional properties
            if self._match(TokenType.LBRACKET):
                properties = self._parse_properties()
                self._consume(TokenType.RBRACKET, "Expected ']'")
                
            self._consume(TokenType.RBRACKET, "Expected ']'")
            
        return RelationshipNode(variable, types, properties, direction)
        
    def _parse_properties(self) -> Dict[str, Any]:
        """Parse a properties map."""
        properties = {}
        
        # Parse key-value pairs
        while True:
            key = self._consume(TokenType.IDENTIFIER, "Expected property name").value
            self._consume(TokenType.COLON, "Expected ':'")
            
            # Parse the value
            if self._match(TokenType.STRING):
                # Remove quotes from string value
                value = self._previous().value[1:-1]
                properties[key] = value
            elif self._match(TokenType.NUMBER):
                # Convert to number
                value_str = self._previous().value
                properties[key] = float(value_str) if '.' in value_str else int(value_str)
            else:
                raise ValueError(f"Expected string or number at position {self._peek().position}")
                
            # Check for more properties
            if not self._match(TokenType.COMMA):
                break
                
        return properties
        
    def _parse_where_clause(self) -> WhereNode:
        """Parse a WHERE clause."""
        self._consume(TokenType.WHERE, "Expected 'WHERE' keyword")
        expression = self._parse_expression()
        return WhereNode(expression)
        
    def _parse_expression(self) -> ExpressionNode:
        """Parse an expression in a WHERE clause."""
        return self._parse_or()
        
    def _parse_or(self) -> ExpressionNode:
        """Parse an OR expression."""
        expr = self._parse_and()
        
        while self._match_value(TokenType.LOGICAL, "OR"):
            operator = self._previous().value
            right = self._parse_and()
            expr = BinaryOpNode(expr, operator, right)
            
        return expr
        
    def _parse_and(self) -> ExpressionNode:
        """Parse an AND expression."""
        expr = self._parse_equality()
        
        while self._match_value(TokenType.LOGICAL, "AND"):
            operator = self._previous().value
            right = self._parse_equality()
            expr = BinaryOpNode(expr, operator, right)
            
        return expr
        
    def _parse_equality(self) -> ExpressionNode:
        """Parse an equality expression."""
        expr = self._parse_comparison()
        
        while self._match_value(TokenType.OPERATOR, "==") or self._match_value(TokenType.OPERATOR, "!="):
            operator = self._previous().value
            right = self._parse_comparison()
            expr = BinaryOpNode(expr, operator, right)
            
        return expr
        
    def _parse_comparison(self) -> ExpressionNode:
        """Parse a comparison expression."""
        expr = self._parse_primary()
        
        while (self._match_value(TokenType.OPERATOR, ">") or 
               self._match_value(TokenType.OPERATOR, ">=") or
               self._match_value(TokenType.OPERATOR, "<") or
               self._match_value(TokenType.OPERATOR, "<=") or
               self._match_value(TokenType.OPERATOR, "=~")):
            operator = self._previous().value
            right = self._parse_primary()
            expr = BinaryOpNode(expr, operator, right)
            
        return expr
        
    def _parse_primary(self) -> ExpressionNode:
        """Parse a primary expression."""
        # Parse property access
        if self._check(TokenType.IDENTIFIER) and self._peek_next().type == TokenType.DOT:
            variable = self._consume(TokenType.IDENTIFIER, "Expected identifier").value
            self._consume(TokenType.DOT, "Expected '.'")
            property_name = self._consume(TokenType.IDENTIFIER, "Expected property name").value
            return PropertyAccessNode(variable, property_name)
            
        # Parse literal values
        if self._match(TokenType.STRING):
            value = self._previous().value[1:-1]  # Remove quotes
            return LiteralNode(value, "string")
            
        if self._match(TokenType.NUMBER):
            value_str = self._previous().value
            value = float(value_str) if '.' in value_str else int(value_str)
            return LiteralNode(value, "number")
            
        # Parse parenthesized expressions
        if self._match(TokenType.LPAREN):
            expr = self._parse_expression()
            self._consume(TokenType.RPAREN, "Expected ')'")
            return expr
            
        # Parse NOT expressions
        if self._match_value(TokenType.LOGICAL, "NOT"):
            operator = self._previous().value
            operand = self._parse_primary()
            return UnaryOpNode(operator, operand)
            
        raise ValueError(f"Unexpected token {self._peek()} at position {self._peek().position}")
        
    def _parse_return_clause(self) -> ReturnNode:
        """Parse a RETURN clause."""
        self._consume(TokenType.RETURN, "Expected 'RETURN' keyword")
        
        items = []
        
        # Parse the first return item
        items.append(self._parse_return_item())
        
        # Parse additional return items
        while self._match(TokenType.COMMA):
            items.append(self._parse_return_item())
            
        return ReturnNode(items)
        
    def _parse_return_item(self) -> Tuple[ExpressionNode, Optional[str]]:
        """Parse a return item."""
        expr = self._parse_expression()
        alias = None
        
        # Parse optional alias (AS identifier)
        if self._check_value(TokenType.IDENTIFIER, "AS"):
            self._advance()  # Consume "AS"
            alias = self._consume(TokenType.IDENTIFIER, "Expected identifier").value
            
        return (expr, alias)
        
    def _is_at_end(self) -> bool:
        """Check if we've reached the end of the tokens."""
        return self._peek().type == TokenType.EOF
        
    def _peek(self) -> Token:
        """Look at the current token."""
        return self.tokens[self.current]
        
    def _peek_next(self) -> Token:
        """Look at the next token."""
        if self.current + 1 >= len(self.tokens):
            return Token(TokenType.EOF, "", -1)
        return self.tokens[self.current + 1]
        
    def _previous(self) -> Token:
        """Get the previous token."""
        return self.tokens[self.current - 1]
        
    def _advance(self) -> Token:
        """Advance to the next token."""
        if not self._is_at_end():
            self.current += 1
        return self._previous()
        
    def _match(self, token_type: TokenType) -> bool:
        """Check if the current token matches the given type and advance if it does."""
        if self._check(token_type):
            self._advance()
            return True
        return False
        
    def _match_value(self, token_type: TokenType, value: str) -> bool:
        """Check if the current token matches the given type and value and advance if it does."""
        if self._check_value(token_type, value):
            self._advance()
            return True
        return False
        
    def _check(self, token_type: TokenType) -> bool:
        """Check if the current token has the given type."""
        if self._is_at_end():
            return False
        return self._peek().type == token_type
        
    def _check_value(self, token_type: TokenType, value: str) -> bool:
        """Check if the current token has the given type and value."""
        if not self._check(token_type):
            return False
        return self._peek().value.upper() == value.upper()
        
    def _consume(self, token_type: TokenType, error_message: str) -> Token:
        """Consume the current token if it has the expected type, or raise an error."""
        if self._check(token_type):
            return self._advance()
            
        raise ValueError(f"{error_message} at position {self._peek().position}")


class Query:
    """
    Represents a parsed query.
    
    This class wraps the parsed AST nodes and provides a convenient interface
    for executing the query.
    """
    
    def __init__(self, query_string: str):
        """
        Initialize a new query from a query string.
        
        Args:
            query_string: The query string to parse
        """
        lexer = Lexer(query_string)
        parser = QueryParser(lexer)
        self.nodes = parser.parse()
        self.match_nodes = [n for n in self.nodes if isinstance(n, MatchNode)]
        self.where_nodes = [n for n in self.nodes if isinstance(n, WhereNode)]
        self.return_nodes = [n for n in self.nodes if isinstance(n, ReturnNode)]
        
    def execute(self, graph):
        """
        Execute the query on the given graph.
        
        Args:
            graph: The graph to query
            
        Returns:
            Query results
        """
        # This will be implemented in the query execution engine
        pass