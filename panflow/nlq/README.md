# PANFlow Natural Language Query (NLQ) Module

This module provides natural language processing capabilities for PANFlow, allowing users to interact with PANFlow using natural language queries instead of remembering specific CLI commands and parameters.

## Architecture

The NLQ module follows a hybrid approach with two processing paths:

1. **AI-powered Processing**: Uses language models via APIs for sophisticated understanding of natural language
2. **Pattern-based Processing**: Uses regex and rule-based logic as a fallback when AI is unavailable

## Files and Components

- `__init__.py`: Exports the main `NLQProcessor` class
- `processor.py`: Main processing logic that coordinates the NLQ pipeline
- `intent_parser.py`: Rule-based intent recognition
- `entity_extractor.py`: Rule-based entity extraction
- `command_mapper.py`: Maps intents and entities to PANFlow commands
- `ai_processor.py`: AI-powered natural language understanding

## Processing Flow

1. User enters a natural language query via CLI
2. `NLQProcessor` tries AI processing if available
3. Falls back to pattern-based processing if AI is unavailable or yields low confidence
4. Maps the intent and entities to a PANFlow command
5. Executes the command and returns results

## AI Integration Details

The `ai_processor.py` module integrates with language models:

- **OpenAI Integration**: Uses the OpenAI API (requires API key in `OPENAI_API_KEY` env var)
- **Anthropic Integration**: Uses the Anthropic API (requires API key in `ANTHROPIC_API_KEY` env var)

The AI processor sends a structured prompt to the language model containing:
- Command reference information
- The user's query
- A request for intent and entity identification

## Adding New Commands

To add support for a new PANFlow command:

1. Update the intent patterns in `intent_parser.py`:
   ```python
   self.intent_patterns = {
       "new_command": [
           r"(do|execute|run).*new.*command",
           r"new command.*with.*parameters",
       ],
       # existing commands...
   }
   ```

2. Add entity extraction patterns in `entity_extractor.py`:
   ```python
   self.entity_patterns = {
       "new_entity_type": {
           "value1": [r"value1", r"v1"],
           "value2": [r"value2", r"v2"],
       },
       # existing entities...
   }
   ```

3. Update the command mapper in `command_mapper.py`:
   ```python
   self.intent_command_map = {
       "new_command": "actual_command_name",
       # existing mappings...
   }
   
   self.command_required_params = {
       "actual_command_name": ["param1", "param2"],
       # existing params...
   }
   ```

4. Update the AI command reference in `ai_processor.py`:
   ```python
   self.command_reference = {
       "commands": [
           {
               "name": "new_command",
               "description": "Description of the new command",
               "parameters": { /* parameter details */ },
               "examples": [ /* example queries */ ]
           },
           # existing commands...
       ]
   }
   ```

## Developers Guide

### Testing Without AI

Set the `use_ai` parameter to `False` when creating the NLQProcessor:

```python
processor = NLQProcessor(use_ai=False)
```

Or use the `--no-ai` flag in the CLI:

```bash
python cli.py nlq query "your query" --no-ai
```

### Debugging

1. **Enable logging**:
   ```bash
   python cli.py nlq query "your query" --verbose
   ```

2. **Examining processing path**:
   The result from `processor.process()` includes a `"processing"` key that tells you whether AI or pattern-based processing was used.

3. **Testing AI processing**:
   To check if the AI processor is working correctly, create a simple test:
   ```python
   from panflow.nlq.ai_processor import AIProcessor
   
   processor = AIProcessor(api_key="your_key", provider="openai")
   result = processor.process_query("show me unused address objects")
   print(result)
   ```

4. **Testing intent parsing**:
   To check if the intent parser is working correctly:
   ```python
   from panflow.nlq.intent_parser import IntentParser
   
   parser = IntentParser()
   intent, confidence = parser.parse("cleanup unused address objects")
   print(f"Intent: {intent}, Confidence: {confidence}")
   ```

### Extending the AI Integration

To add support for a new AI provider:

1. Update the `_process_with_provider` method in `ai_processor.py`
2. Add environment variable handling in `processor.py`
3. Update the command-line options in `nlq_commands.py`