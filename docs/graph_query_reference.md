# PAN-OS Graph Query Language Reference Guide

This reference guide provides detailed information on the syntax, node types, properties, operators, and usage patterns for the PAN-OS Graph Query Language (PQL).

## Query Structure

A basic PQL query follows this structure:

```
MATCH (node_variable:node_type)
[WHERE filter_conditions]
RETURN return_items
```

Where:
- `MATCH` specifies the patterns to match in the graph
- `WHERE` (optional) filters the results based on conditions
- `RETURN` specifies what to return from the query

## Node Types

These are the main node types available in the graph:

| Node Type | Description | Variable Convention |
|-----------|-------------|---------------------|
| `address` | Address objects | `a` or `addr` |
| `address-group` | Address groups | `g` or `grp` |
| `service` | Service objects | `s` or `svc` |
| `service-group` | Service groups | `sg` or `svcgrp` |
| `security-rule` | Security rules | `r` or `rule` |
| `nat-rule` | NAT rules | `n` or `nat` |
| `application` | Application objects | `app` |
| `application-group` | Application groups | `appgrp` |
| `tag` | Tags | `t` or `tag` |

Example:
```
MATCH (a:address)
```

## Node Properties

Common properties for all nodes:

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique identifier for the node |
| `name` | String | Name of the object |
| `type` | String | Type of the object |
| `edges_out` | Array | Outgoing relationships to other nodes |
| `edges_in` | Array | Incoming relationships from other nodes |

### Address Properties

| Property | Type | Description |
|----------|------|-------------|
| `value` | String | IP address, range, or FQDN value |
| `addr_type` | String | Type of address (ip-netmask, ip-range, fqdn) |

### Service Properties

| Property | Type | Description |
|----------|------|-------------|
| `protocol` | String | Protocol (tcp, udp) |
| `port` | String | Port number or range |

### Rule Properties

| Property | Type | Description |
|----------|------|-------------|
| `action` | String | Action (allow, deny, etc.) |
| `from` | String | Source zone |
| `to` | String | Destination zone |
| `description` | String | Rule description |
| `disabled` | Boolean | Whether the rule is disabled |

## Relationship Types

Relationships between nodes are represented as edges in the graph:

| Relationship Type | Source | Target | Description |
|-------------------|--------|--------|-------------|
| `contains` | Group | Member | Group contains a member object |
| `uses-source` | Rule | Address/Group | Rule uses an address as source |
| `uses-destination` | Rule | Address/Group | Rule uses an address as destination |
| `uses-service` | Rule | Service/Group | Rule uses a service |
| `uses-application` | Rule | Application | Rule uses an application |

## Edge Properties

An edge has these properties:

| Property | Type | Description |
|----------|------|-------------|
| `relation` | String | Type of relationship |
| `source` | String | Source node ID (for edges_in) |
| `target` | String | Target node ID (for edges_out) |

## Operators

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equal to | `a.name == "web-server"` |
| `!=` | Not equal to | `a.name != "test"` |
| `>` | Greater than | `r.edges_out.length > 5` |
| `>=` | Greater than or equal | `r.edges_out.length >= 5` |
| `<` | Less than | `r.edges_out.length < 5` |
| `<=` | Less than or equal | `r.edges_out.length <= 5` |
| `=~` | Regular expression match | `a.name =~ "^web-.*"` |

### Logical Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `AND` | Logical AND | `a.name == "web" AND a.addr_type == "ip-netmask"` |
| `OR` | Logical OR | `a.name == "web" OR a.name == "db"` |
| `NOT` | Logical NOT | `NOT (a.name == "test")` |

## CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `execute` | Execute a query | `query execute -c config.xml -q "MATCH (a:address) RETURN a.name"` |
| `verify` | Verify query syntax | `query verify -q "MATCH (a:address) RETURN a.name"` |
| `interactive` | Start interactive session | `query interactive -c config.xml` |
| `example` | Show example queries | `query example` |

### Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `-c, --config` | Configuration file path | `-c config.xml` |
| `-q, --query` | Query string | `-q "MATCH (a:address) RETURN a.name"` |
| `-f, --format` | Output format (table, json, csv) | `-f json` |
| `-o, --output` | Output file path | `-o results.json` |

## Advanced Usage

### Multiple MATCH Clauses

You can use multiple MATCH clauses to match different node types:

```
MATCH (r:security-rule)
MATCH (a:address)
WHERE r.name == "policy1" AND a.name == "web-server"
RETURN r.name, a.name
```

### Working with Relationships

To check if a relationship exists, you need to work with the `edges_out` and `edges_in` properties:

```
MATCH (r:security-rule)
MATCH (a:address)
WHERE r.edges_out CONTAINS {target: a.id, relation: "uses-destination"}
RETURN r.name, a.name
```

Note: Direct relationship patterns like `(a)-[:contains]->(b)` are not supported in the current version. Always use the edge properties.

Alternative approach for finding relationships:

```
MATCH (r:security-rule)
MATCH (a:address)
WHERE r.id IN a.edges_in.source
RETURN r.name, a.name
```

### Using Regular Expressions

Regular expressions are useful for pattern matching:

```
MATCH (a:address)
WHERE a.name =~ "^web-.*" AND a.value =~ "10\\.1\\..*"
RETURN a.name, a.value
```

### Aggregation

Basic aggregation is supported:

```
MATCH (a:address)
RETURN a.addr_type, COUNT(*)
```

## Limitations and Known Issues

The current implementation of the graph query language has some limitations to be aware of:

1. **Relationship Pattern Syntax**: Direct relationship patterns like `(a)-[:contains]->(b)` are not supported in the current version. Use `edges_out` and `edges_in` properties instead.

2. **Limited String Operations**: The `CONTAINS` and `STARTS WITH` keywords are not supported. Use regular expressions with `=~` instead:
   - Instead of `a.name CONTAINS "web"`, use `a.name =~ ".*web.*"`
   - Instead of `a.name STARTS WITH "web"`, use `a.name =~ "^web.*"`

3. **Strict Equality Operator**: Only use `==` for equality comparison, not `=`. Using `=` will result in syntax errors.

4. **Limited Aggregation**: Only basic aggregation functions like `COUNT` are supported.

## Best Practices

1. **Be specific**: Use node types and properties to narrow down results
2. **Start simple**: Begin with basic queries and add complexity as needed
3. **Use appropriate output format**: Use table for simple results, JSON for complex data
4. **Save results**: Export results to files for further analysis
5. **Use regular expressions**: For flexible pattern matching
6. **Check relationships directly**: Use edges_out and edges_in to examine relationships
7. **Use the verification tool**: Validate your queries before execution
8. **Escape special characters**: When using regular expressions, remember to escape special characters (e.g., `10\\.1\\..*` for IP patterns)
9. **Check syntax first**: Run your query with `query verify` before executing to catch syntax issues