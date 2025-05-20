# PAN-OS Graph Query Language

The PAN-OS Graph Query Language (PQL) is a specialized query language designed for analyzing PAN-OS firewall configurations. It allows you to represent the configuration as a graph and perform powerful queries to analyze relationships between objects, rules, and other components.

## Current Implementation Limitations

The current implementation supports a subset of the full PQL syntax:

1. Basic pattern matching with `MATCH (a:type)` syntax
2. Multiple independent `MATCH` clauses to select different types of nodes
3. Filtering with `WHERE` clauses
4. Returning node properties with `RETURN`

There are several important limitations to be aware of:

1. **Relationship Patterns**: Direct relationship traversal in the query syntax (like `MATCH (a)-[:rel]->(b)`) is not supported in the current implementation. Instead, use multiple MATCH clauses and filter with WHERE clauses, or query the relationship information directly with `node.edges_out` and `node.edges_in`.

2. **String Operations**: String operations like `CONTAINS` and `STARTS WITH` are not supported. Use regular expressions with the `=~` operator instead:
   - Instead of `a.name CONTAINS "web"`, use `a.name =~ ".*web.*"`
   - Instead of `a.name STARTS WITH "web"`, use `a.name =~ "^web.*"`

3. **Equality Operator**: Only use the double equals (`==`) for equality comparison. Using a single equals (`=`) will result in syntax errors.

4. **Special Characters in Regex**: When using regular expressions with the `=~` operator, you must escape special characters like periods with a double backslash: `a.value =~ ".*10\\.10\\..*"`

## Overview

PQL uses a syntax inspired by graph query languages like Cypher. The language treats configuration objects as nodes in a graph and the relationships between them as edges. This allows you to easily express queries about the configuration structure and find patterns that would be difficult to identify through traditional means.

## Core Concepts

### Nodes and Relationships

In PQL, configuration objects are represented as nodes in the graph:

- Address objects
- Address groups
- Service objects
- Service groups
- Security rules
- NAT rules

Relationships between these objects are represented as edges in the graph:

- Address group to address (contains)
- Service group to service (contains)
- Security rule to address (uses-source, uses-destination)
- Security rule to service (uses-service)
- Security rule to application (uses-application)
- NAT rule to address (uses-source, uses-destination)
- NAT rule to service (uses-service)

### Query Structure

A typical PQL query consists of the following clauses:

1. `MATCH` - Specifies patterns to match in the graph
2. `WHERE` - Filters the results based on conditions
3. `RETURN` - Specifies what to return from the query

Example:

```
MATCH (r:security-rule)
MATCH (a:address)
WHERE a.name == "web-server" AND r.edges_out CONTAINS {target: a.id, relation: "uses-source"}
RETURN r.name
```

This query finds all security rules that use "web-server" as a source address.

## Pattern Syntax

### Node Patterns

Nodes are specified in parentheses:

```
(variable:type)
```

- `variable` (optional) - A variable name to refer to the node
- `type` - The type of the node (e.g., address, service, security-rule)

Example:

```
(a:address)
```

### Relationship Patterns

Relationships are specified with square brackets and arrows:

```
-[:type]->
```

- `type` - The type of the relationship (e.g., contains, uses-source)

Example:

```
(g:address-group)-[:contains]->(a:address)
```

### Property Access

Node properties can be accessed using the dot notation:

```
node.property
```

Example:

```
a.name, a.value
```

## CLI Usage

The PQL is integrated into the PANFlow CLI through the `query` command.

### Execute a Query

```
panflow query execute -c config.xml -q "MATCH (a:address) RETURN a.name, a.value"
```

This command executes the query on the specified configuration file and displays the results as a table.

### Output Formats

You can specify the output format using the `--format` option:

```
panflow query execute -c config.xml -q "MATCH (a:address) RETURN a.name, a.value" --format json
```

Supported formats:
- table (default)
- json
- csv

### Interactive Mode

You can also use the interactive mode to execute multiple queries:

```
panflow query interactive -c config.xml
```

In interactive mode, you can enter queries and see the results immediately.

### Verify Query Syntax

To verify the syntax of a query without executing it:

```
panflow query verify -q "MATCH (a:address) RETURN a.name"
```

### Examples

To see examples of PQL queries:

```
panflow query example
```

### Using with Device Group Context

When querying Panorama configurations, you can specify device group context to limit the query to policies within that device group:

```
panflow query execute -c panorama.xml --device-type panorama --context device_group --device-group DG1 -q "MATCH (r:security-rule) RETURN r.name, r.action"
```

The CLI will automatically modify the query to filter for policies in the specified device group.

## Example Queries

### Device Group Specific Queries

#### Find all policies in a device group

```
MATCH (r:security-rule)
WHERE r.device_group == "DG1"
RETURN r.name, r.action
```

#### Find disabled policies in a device group

```
MATCH (r:security-rule)
WHERE r.device_group == "DG1" AND r.disabled == "yes"
RETURN r.name
```

### Find all address objects

```
MATCH (a:address)
RETURN a.name, a.value, a.addr_type
```

### Find all address groups and their members

```
MATCH (g:address-group)
MATCH (a:address)
WHERE g.edges_out CONTAINS {target: a.id, relation: "contains"}
RETURN g.name, a.name
```

### Find all security rules using a specific address

```
MATCH (r:security-rule)
MATCH (a:address)
WHERE a.name == "web-server" AND
      (r.edges_out CONTAINS {target: a.id, relation: "uses-source"} OR
       r.edges_out CONTAINS {target: a.id, relation: "uses-destination"})
RETURN r.name
```

### Find all unused address objects

```
MATCH (a:address)
MATCH (r:security-rule)
MATCH (g:address-group)
WHERE NOT EXISTS(r.edges_out[*] ? (@.target == a.id AND (@.relation == "uses-source" OR @.relation == "uses-destination")))
  AND NOT EXISTS(g.edges_out[*] ? (@.target == a.id AND @.relation == "contains"))
RETURN a.name
```

### Find rules allowing specific services

```
MATCH (r:security-rule)
MATCH (s:service)
WHERE (s.name == "http" OR s.name == "https") AND
      r.edges_out CONTAINS {target: s.id, relation: "uses-service"}
RETURN r.name
```

## Advanced Usage

### Find services referenced by security rules but not defined

```
MATCH (r:security-rule)
MATCH (s:service)
WHERE s.placeholder == true AND r.edges_out CONTAINS {target: s.id, relation: "uses-service"}
RETURN s.name, r.name
```

### Find security rules that use address groups

```
MATCH (r:security-rule)
MATCH (g:address-group)
WHERE r.edges_out CONTAINS {target: g.id, relation: "uses-source"} OR
      r.edges_out CONTAINS {target: g.id, relation: "uses-destination"}
RETURN r.name, g.name
```

### Find objects used in both security and NAT rules

```
MATCH (sr:security-rule)
MATCH (nr:nat-rule)
MATCH (a:address)
WHERE (sr.edges_out CONTAINS {target: a.id, relation: "uses-source"} OR
       sr.edges_out CONTAINS {target: a.id, relation: "uses-destination"}) AND
      (nr.edges_out CONTAINS {target: a.id, relation: "uses-source"} OR
       nr.edges_out CONTAINS {target: a.id, relation: "uses-destination"})
RETURN a.name, sr.name, nr.name
```

## Query Language Reference

### Operators

- `==` - Equal
- `!=` - Not equal
- `>` - Greater than
- `>=` - Greater than or equal
- `<` - Less than
- `<=` - Less than or equal
- `=~` - Regular expression match

### Logical Operators

- `AND` - Logical AND
- `OR` - Logical OR
- `NOT` - Logical NOT

### Node Types

- `address` - Address object
- `address-group` - Address group
- `service` - Service object
- `service-group` - Service group
- `security-rule` - Security rule
- `nat-rule` - NAT rule
- `application` - Application object

### Relationship Types

- `contains` - Group to member relationship
- `uses-source` - Rule to source object relationship
- `uses-destination` - Rule to destination object relationship
- `uses-service` - Rule to service object relationship
- `uses-application` - Rule to application object relationship