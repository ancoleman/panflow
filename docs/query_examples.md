# PAN-OS Graph Query Language Examples

This document provides 20 example usages of the PAN-OS Graph Query Language (PQL), explains operators, and defines the various node prefixes used in queries.

## Understanding the Basics

### Query Structure

A typical PQL query consists of three main parts:

1. **MATCH** - Specifies what objects to match in the configuration
2. **WHERE** - Filters the matched objects (optional)
3. **RETURN** - Specifies what information to return

Example:
```
MATCH (a:address) 
WHERE a.name == "shared-dgs" 
RETURN a.name, a.value
```

### Node Variables

Node variables are defined in the MATCH clause and serve as references to matched objects:

- `a` refers to address objects when declared as `(a:address)`
- `r` refers to rule objects when declared as `(r:security-rule)`
- `g` refers to group objects when declared as `(g:address-group)`

These are just conventions; you can use any variable name:
```
MATCH (myaddress:address) RETURN myaddress.name
```

### Node Properties

Properties are accessed using dot notation:

```
a.name     # Name of an address object
r.edges_out  # Outgoing relationships from a rule
g.id       # ID of a group
```

Common properties include:
- `name` - The name of the object
- `type` - The type of the object
- `value` - The value for address objects
- `addr_type` - The type of address (ip-netmask, ip-range, etc.)
- `edges_out` - Outgoing relationships to other objects
- `edges_in` - Incoming relationships from other objects

## Operators

### Comparison Operators

- `==` - Equal to
  ```
  WHERE a.name == "web-server"
  ```

- `!=` - Not equal to
  ```
  WHERE a.addr_type != "ip-range"
  ```

- `>`, `>=`, `<`, `<=` - Greater than, greater than or equal, less than, less than or equal
  ```
  WHERE r.edges_out.length > 5
  ```

- `=~` - Regular expression match
  ```
  WHERE a.value =~ "10\\..*"
  ```

### Logical Operators

- `AND` - Logical AND
  ```
  WHERE a.name == "web-server" AND a.addr_type == "ip-netmask"
  ```

- `OR` - Logical OR
  ```
  WHERE a.name == "web-server" OR a.name == "db-server"
  ```

- `NOT` - Logical NOT
  ```
  WHERE NOT (a.name == "test")
  ```

## 20 Example Usages

### 1. List all address objects

```bash
python cli.py query execute -c config.xml -q "MATCH (a:address) RETURN a.name, a.value, a.addr_type"
```

This query matches all address objects and returns their names, values, and address types.

### 2. Find an address object by name

```bash
python cli.py query execute -c config.xml -q "MATCH (a:address) WHERE a.name == 'web-server' RETURN a.name, a.value"
```

This query matches address objects with the name "web-server" and returns the name and value.

### 3. Find address objects with a specific IP pattern

```bash
python cli.py query execute -c config.xml -q "MATCH (a:address) WHERE a.value =~ '10\\.1\\..*' RETURN a.name, a.value"
```

This query uses a regular expression to match address objects with values starting with "10.1." and returns their names and values.

### 4. Find all security rules

```bash
python cli.py query execute -c config.xml -q "MATCH (r:security-rule) RETURN r.name"
```

This query matches all security rules and returns their names.

### 5. Find security rules with a specific word in the name

```bash
python cli.py query execute -c config.xml -q "MATCH (r:security-rule) WHERE r.name =~ '.*allow.*' RETURN r.name"
```

This query uses a regular expression to match security rules with "allow" in their names.

### 6. List all address groups

```bash
python cli.py query execute -c config.xml -q "MATCH (g:address-group) RETURN g.name"
```

This query matches all address groups and returns their names.

### 7. Find address objects used in a specific security rule

```bash
python cli.py query execute -c config.xml -q "MATCH (r:security-rule) WHERE r.name == 'test-shared policy' RETURN r.name, r.edges_out" --format json
```

This query finds the security rule named "test-shared policy" and returns its outgoing relationships, which show the objects it references.

### 8. Find security rules using a specific address

```bash
python cli.py query execute -c config.xml -q "MATCH (r:security-rule) MATCH (a:address) WHERE a.name == 'shared-dgs' AND r.edges_out CONTAINS {target: a.id, type: 'uses-destination'} RETURN r.name"
```

This advanced query finds security rules that use the address "shared-dgs" as a destination.

### 9. List all services and their ports

```bash
python cli.py query execute -c config.xml -q "MATCH (s:service) RETURN s.name, s.protocol, s.port"
```

This query matches all service objects and returns their names, protocols, and ports.

### 10. Find unused address objects

```bash
python cli.py query execute -c config.xml -q "MATCH (a:address) WHERE a.edges_in.length == 0 RETURN a.name, a.value"
```

This query finds address objects that have no incoming relationships, meaning they are not referenced by any rule or group.

### 11. Find security rules with multiple destination addresses

```bash
python cli.py query execute -c config.xml -q "MATCH (r:security-rule) WHERE r.edges_out.length > 2 RETURN r.name, r.edges_out.length" --format json
```

This query finds security rules that reference more than 2 objects and returns the rule name and the count of referenced objects.

### 12. Find address objects that start with a specific prefix

```bash
python cli.py query execute -c config.xml -q "MATCH (a:address) WHERE a.name =~ '^web-.*' RETURN a.name, a.value"
```

This query uses a regular expression to find address objects with names starting with "web-".

### 13. Count security rules by their first word

```bash
python cli.py query execute -c config.xml -q "MATCH (r:security-rule) RETURN r.name.split('-')[0], COUNT(*)" --format json
```

This advanced query splits rule names by "-" and counts rules by their first word.

### 14. Find addresses in a specific subnet

```bash
python cli.py query execute -c config.xml -q "MATCH (a:address) WHERE a.addr_type == 'ip-netmask' AND a.value =~ '192\\.168\\.1\\..*' RETURN a.name, a.value"
```

This query finds address objects in the 192.168.1.x subnet.

### 15. Find security rules that allow HTTP or HTTPS

```bash
python cli.py query execute -c config.xml -q "MATCH (r:security-rule) MATCH (s:service) WHERE s.name == 'http' OR s.name == 'https' RETURN r.name, s.name"
```

This query finds security rules that allow HTTP or HTTPS services.

### 16. Visualize the relationship between a rule and its references

```bash
python cli.py query execute -c config.xml -q "MATCH (r:security-rule) WHERE r.name == 'test-shared policy' RETURN r.name, r.edges_out" --format json
```

This query returns detailed information about the relationships between a rule and the objects it references, in JSON format for better visualization.

### 17. Find address objects with no value defined (placeholder objects)

```bash
python cli.py query execute -c config.xml -q "MATCH (a:address) WHERE a.value == null RETURN a.name"
```

This query finds address objects that have no value defined, often indicating placeholder objects.

### 18. Find address groups that contain a specific address

```bash
python cli.py query execute -c config.xml -q "MATCH (g:address-group) MATCH (a:address) WHERE a.name == 'shared-dgs' AND g.edges_out CONTAINS {target: a.id, type: 'contains'} RETURN g.name"
```

This advanced query finds address groups that contain the address "shared-dgs".

### 19. Find rules with a specific source zone

```bash
python cli.py query execute -c config.xml -q "MATCH (r:security-rule) WHERE r.from == 'trust' RETURN r.name"
```

This query finds security rules with a source zone of "trust".

### 20. Export all configuration objects to JSON

```bash
python cli.py query execute -c config.xml -q "MATCH (n) RETURN n.type, n.name, n" --format json --output config_objects.json
```

This query matches all nodes in the graph, regardless of type, and exports them to a JSON file with their type, name, and all properties.

## Interactive Mode

For exploratory analysis, you can use the interactive mode:

```bash
python cli.py query interactive -c config.xml
```

In interactive mode, you can enter queries one after another and see the results immediately. This is useful for exploring the configuration and refining your queries iteratively.

## Tips for Effective Querying

1. **Start simple**: Begin with basic queries and add complexity as needed.
2. **Use JSON format** for complex data: When examining relationships, use `--format json` for better readability.
3. **Check node properties**: If you're unsure what properties are available for a node, query it with `RETURN n` to see all properties.
4. **Use regex patterns**: Regular expressions are powerful for finding patterns in names and values.
5. **Combine multiple MATCH clauses**: To create more complex queries, use multiple MATCH clauses with shared variables.
6. **Export results**: Use `--output filename.json` or `--output filename.csv` to save query results for further analysis.

## Troubleshooting

- If a query returns no results, check your spelling and syntax.
- If relationships aren't showing up as expected, try examining them directly with `node.edges_out` or `node.edges_in`.
- Use the `verify` command to check your query syntax before executing it.