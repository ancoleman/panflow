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

## Usage

### Basic Query

```bash
# Process a natural language query (view-only operation - no output file needed)
python cli.py nlq query "show me all unused address objects" --config firewall.xml

# Cleanup operation requires an output file
python cli.py nlq query "cleanup unused service objects" --config firewall.xml --output cleaned.xml

# Use dry run mode via natural language
python cli.py nlq query "show me all unused objects but don't make any changes"

# Use AI-powered processing (if available)
python cli.py nlq query "find any objects not being used anywhere in the config"

# Force using pattern-based processing instead of AI
python cli.py nlq query "find duplicate address objects" --no-ai

# Specify a different AI provider and model
python cli.py nlq query "show me unused objects" --ai-provider anthropic --ai-model claude-3-haiku-20240307
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

Found 5 duplicate objects across 2 values
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

### Cleanup Operations

- "Cleanup unused address objects"
- "Remove all disabled security rules"
- "Delete unused service objects but don't make changes yet"
- "Find and cleanup unused address-groups"

### Reporting

- "Show me all unused address objects"
- "List disabled security policies"
- "Find duplicate address objects"
- "What address objects are not used anywhere?"

### Contextual Operations

- "Cleanup unused objects in device group DG1"
- "Show disabled policies in vsys1"
- "Find unused objects in the shared context"

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
3. **Command Mapping**: Mapping intent and entities to PANFlow commands
4. **Command Execution**: Executing the command and returning results

## Extending the NLQ Module

### Adding New Query Types

To add support for new query types:

1. Add new patterns to the intent parser (`intent_parser.py`)
2. Add entity extraction for new entity types (`entity_extractor.py`)
3. Update the command mapper to handle the new intent (`command_mapper.py`)
4. Update the AI processor command reference (`ai_processor.py`)

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
```

## Future Enhancements

- **Local embedding models**: Add support for offline operation with smaller models
- **Context-aware conversations**: Better maintain context across multiple queries
- **Clarification questions**: Ask for missing information in ambiguous queries
- **Custom vocabulary**: Allow users to define their own terminology
- **Multi-language support**: Process queries in multiple languages
- **Voice input**: Add support for speech-to-text for voice commands