# Natural Language Query (NLQ) Module for PANFlow

The Natural Language Query (NLQ) module allows users to interact with PANFlow using natural language instead of remembering CLI commands and parameters.

## Features

- **Natural language understanding**: Interpret commands and queries in plain English
- **AI-powered processing**: Use language models for advanced natural language understanding
- **Pattern-based fallback**: Continue working even without AI availability
- **Intent detection**: Identify what the user is trying to accomplish
- **Entity extraction**: Extract key information like object types, policy types, and contexts
- **Command mapping**: Translate natural language to PANFlow commands
- **Interactive mode**: Maintain context across multiple queries
- **Suggestions**: Provide helpful suggestions when queries are ambiguous
- **Dry run support**: Preview changes without modifying configurations

## Usage

### Basic Query

```bash
# Process a natural language query (view-only operation - no output file needed)
python cli.py nlq query "show me all unused address objects" --config firewall.xml

# Cleanup operation requires an output file
python cli.py nlq query "cleanup unused service objects" --config firewall.xml --output cleaned.xml

# Use dry run mode via CLI flag
python cli.py nlq query "cleanup unused address objects" --config firewall.xml --output cleaned.xml --dry-run

# Use dry run mode via natural language
python cli.py nlq query "show me all unused objects but don't make any changes" --config firewall.xml

# Use AI-powered processing (if available)
python cli.py nlq query "find any objects not being used anywhere in the config" --config firewall.xml

# Force using pattern-based processing instead of AI
python cli.py nlq query "find duplicate address objects" --config firewall.xml --no-ai

# Specify a different AI provider and model
python cli.py nlq query "show me unused objects" --config firewall.xml --ai-provider anthropic --ai-model claude-3-haiku-20240307
```

### Output Formatting

The NLQ module provides user-friendly output formatting based on the type of operation:

#### View-only operations

```
Intent: list_unused_objects
Command executed successfully

Found 3 unused objects:
  - unused-address1
  - unused-address2
  - unused-service1
```

#### Cleanup operations

```
Intent: cleanup_unused_objects
Command executed successfully

Removed 3 objects:
  - unused-address1
  - unused-address2
  - unused-service1

Configuration saved to: cleaned.xml
```

#### Duplicate findings

```
Intent: find_duplicates
Command executed successfully

Found 5 duplicated address objects across 2 unique values:
  - test-addr1: ip:10.0.0.1/32
  - test-addr2: ip:10.0.0.1/32
  - test-addr3: ip:10.0.0.1/32
  - backup-addr1: ip:192.168.1.1/32
  - backup-addr2: ip:192.168.1.1/32
```

#### Duplicate cleanup

```
Intent: cleanup_duplicate_objects
Command executed successfully

Found 5 duplicated address objects across 2 unique values.
Will remove 3 duplicate objects:
  - test-addr2: ip:10.0.0.1/32 (duplicate of test-addr1)
  - test-addr3: ip:10.0.0.1/32 (duplicate of test-addr1)
  - backup-addr2: ip:192.168.1.1/32 (duplicate of backup-addr1)

Configuration saved to: deduped_config.xml
```

### Interactive Mode

```bash
# Start an interactive session
python cli.py nlq interactive --config firewall.xml

# Example session
PANFlow> show me all unused address objects
Intent: list_unused_objects
Command executed successfully

Found 15 unused objects:
  - unused-addr1
  - unused-addr2
  - unused-addr3
  - ...10 more...

PANFlow> cleanup these objects
Intent: cleanup_unused_objects
Command executed successfully

Removed 15 objects:
  - unused-addr1
  - unused-addr2
  - unused-addr3
  - ...10 more...

Configuration saved to: cleaned.xml

PANFlow> list all security rules that use the any source
Intent: list_policies
Command executed successfully

Found 3 security_rules:
  - allow-web
  - allow-ssh
  - allow-rdp
```

### AI Integration

For AI-powered natural language processing, you need to set up API keys:

#### OpenAI Setup

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your_api_key

# Specify a model at runtime (default is gpt-3.5-turbo)
python cli.py nlq query "your query" --ai-model gpt-4
```

#### Anthropic Setup

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY=your_api_key

# Use Anthropic's Claude
python cli.py nlq query "your query" --ai-provider anthropic
```

### Help

```bash
# Get help and examples for NLQ
python cli.py nlq help
```

## Supported Query Types

The NLQ module supports the following types of queries:

### Object Management

- "List all address objects"
- "Show me service objects"
- "Find address objects with 10.0.0 in them"
- "Show all application objects"
- "List address-groups"
- "Show service-groups"

### Policy Management

- "List security policies" 
- "Show security rules"
- "List NAT rules"
- "Show all pre security rules"
- "Show security post rules"
- "List security rules that use HTTP service"

### Cleanup Operations

- "Cleanup unused address objects"
- "Remove all disabled security rules"
- "Delete unused service objects but don't make changes yet"
- "Find and cleanup unused address-groups"
- "Cleanup disabled nat rules"
- "Remove disabled security policies"

### Finding Unused & Disabled Items

- "Show me all unused address objects"
- "List disabled security policies"
- "Find unused service groups"
- "What address objects are not used anywhere?"
- "Show me disabled security rules"
- "Find disabled NAT policies"

### Deduplication

- "Find duplicate address objects"
- "Show me duplicate service objects"
- "Find all duplicate objects"
- "Show me address objects with the same IP"
- "Clean up duplicated service objects"
- "Deduplicate address objects"
- "Consolidate duplicate application objects"
- "Remove duplicate tag objects"

### Contextual Operations

- "Cleanup unused objects in device group DG1"
- "Show disabled policies in vsys1"
- "Find unused objects in the shared context"
- "Find duplicate objects in device group DG1"

### Dry Run Queries

- "Cleanup unused objects but don't make changes"
- "Cleanup disabled policies in dry run mode"
- "Preview what unused objects would be removed"
- "Simulate cleanup of unused service objects"

## How It Works

### Hybrid Processing Approach

The NLQ module uses a hybrid approach for processing queries:

1. **AI-powered Processing** (when available):
   - Uses language models via APIs
   - Provides sophisticated understanding of natural language
   - Handles complex and varied phrasings
   - Falls back to pattern-based processing if unavailable

2. **Pattern-based Processing** (fallback):
   - Uses regular expressions and rule-based logic
   - Works without external dependencies
   - Handles common query patterns reliably

### Processing Pipeline

The NLQ module follows a pipeline architecture:

1. **Intent Parsing**: Identifying the user's intent from the query
2. **Entity Extraction**: Extracting relevant entities from the query
   - Detects object types (address, service, application, etc.)
   - Identifies contexts (device groups, vsys)
   - Recognizes special flags (like duplicate detection)
3. **Command Mapping**: Mapping intent and entities to PANFlow commands
4. **Command Execution**: Executing the command and returning results

### Deduplication Process

The NLQ module's deduplication capability follows these steps:

1. **Detecting Duplicate Requests**:
   - Recognizes phrases like "duplicated objects", "objects with same values", etc.
   - Sets the `show_duplicates` flag during entity extraction

2. **Finding Duplicates**:
   - Uses the DeduplicationEngine to identify duplicates by object type
   - Groups objects by their values (IP, port, protocol, etc.)
   - Considers objects duplicates when they have the same functional values

3. **Deduplication Strategy**:
   - Uses a "keep first occurrence" strategy by default
   - Marks all subsequent duplicates for removal
   - Preserves references by updating dependencies to use the kept object

4. **Processing or Simulation**:
   - In dry-run mode, shows which objects would be removed
   - In normal mode, performs the actual deduplication
   - Updates all references to maintain configuration integrity

## Dry Run Mode

The NLQ module supports dry run mode, allowing you to preview changes without modifying the configuration:

1. **CLI Parameter**: Use the `--dry-run` flag with any query:
   ```bash
   python cli.py nlq query "cleanup unused objects" --config config.xml --output clean.xml --dry-run
   ```

2. **Natural Language**: Include "dry run" or similar phrases in your query:
   ```bash
   python cli.py nlq query "cleanup unused objects in dry run mode" --config config.xml --output clean.xml
   ```

3. **Behavior**:
   - Shows what changes would be made without actually modifying files
   - Identifies which objects/policies would be affected
   - Works with all cleanup and modification operations
   - No output file is created when in dry run mode

## Example Queries

Here are 30 example NLQ commands demonstrating the various capabilities:

### Object Listing and Manipulation

1. `list all address objects`
2. `show me service objects`
3. `find address objects with 10.0.0 in them`
4. `list all application objects`
5. `show all address-groups`
6. `list objects in device group DG1`
7. `show me all service-groups`
8. `find tag objects`

### Policy Queries

9. `list all security policies`
10. `show disabled security rules`
11. `find nat rules`
12. `show pre security rules`
13. `list security post rules`
14. `show security rules that use the any source`
15. `find policies that use HTTP service`
16. `list nat policies in device group DG1`

### Cleanup Operations

17. `cleanup unused address objects`
18. `remove all disabled security rules`
19. `cleanup unused service objects in dry run mode`
20. `find and cleanup unused address-groups`
21. `cleanup disabled nat rules`
22. `remove disabled security policies but don't apply changes`
23. `cleanup unused objects in device group DG1`
24. `remove unused objects but just show what would be deleted`

### Finding Unused & Disabled Items

25. `show me all unused address objects`
26. `list disabled security policies`
27. `find unused service groups`
28. `show me disabled security rules in device group DG1`
29. `find disabled NAT policies`
30. `list all unused objects in the configuration`

### Deduplication

31. `find duplicate address objects`
32. `show me duplicate service objects`
33. `find all duplicate objects`
34. `show me address objects with the same IP`
35. `find objects with identical values`
36. `list duplicate service objects in device group DG1`
37. `identify address objects with duplicate IPs`

### Combined Operations

38. `find and cleanup duplicate address objects`
39. `cleanup all duplicated service objects`
40. `show me unused objects and cleanup them`
41. `list disabled rules and remove them`
42. `deduplicate address objects with the same IP`

## Extending the NLQ Module

### Adding New Query Types

To add support for new query types:

1. Add new patterns to the intent parser (`intent_parser.py`)
2. Add entity extraction for new entity types (`entity_extractor.py`)
3. Update the command mapper to handle the new intent (`command_mapper.py`)
4. Update the AI processor command reference (`ai_processor.py`)

### Extending Deduplication Support

To enhance deduplication capabilities:

1. Add new deduplication strategies to the `DeduplicationEngine` class
2. Update the intent patterns for capturing deduplication preferences
3. Extend entity extraction to recognize strategy specifications
4. Enhance the command mapping for deduplication operations
5. Update the processor to handle different deduplication strategies

### Improving AI Integration

The AI integration can be enhanced by:

1. **Expanding the command reference** with more examples and parameters
2. **Adding more advanced LLM prompting** for better instruction following
3. **Implementing feedback mechanisms** to improve over time
4. **Supporting more AI providers** beyond OpenAI and Anthropic

## Configuration Options

The NLQ module can be configured through environment variables:

```bash
# Set the default AI provider
export PANFLOW_AI_PROVIDER=openai  # or anthropic

# Set the default AI model
export PANFLOW_AI_MODEL=gpt-4  # or claude-3-haiku-20240307
```

Or through CLI parameters:

```bash
# Enable or disable AI processing
python cli.py nlq query "your query" --ai  # or --no-ai

# Specify AI provider
python cli.py nlq query "your query" --ai-provider openai

# Specify AI model
python cli.py nlq query "your query" --ai-model gpt-4

# Enable dry run mode
python cli.py nlq query "your query" --dry-run
```

## Future Enhancements

- **Local embedding models**: Add support for offline operation with smaller models
- **Context-aware conversations**: Better maintain context across multiple queries
- **Clarification questions**: Ask for missing information in ambiguous queries
- **Custom vocabulary**: Allow users to define their own terminology
- **Multi-language support**: Process queries in multiple languages
- **Voice input**: Add support for speech-to-text for voice commands
- **Advanced deduplication strategies**: Support for different deduplication strategies (keep first, keep newest, etc.)
- **Cross-object-type deduplication**: Intelligent consolidation of objects across different types
- **Similarity-based deduplication**: Find and consolidate objects that are similar but not exact duplicates