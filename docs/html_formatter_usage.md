# HTML Formatter Usage Guide

The PANFlow CLI provides rich HTML report generation capabilities. This guide explains how to use and extend the HTML output functionality.

## Basic Usage

Most CLI commands support the `--format html` option which will generate HTML output:

```bash
python cli.py query execute --config config.xml --query "MATCH (a:address) RETURN a.name, a.value" --format html --output report.html
```

## HTML Report Features

HTML reports include:

1. **Descriptive Titles**: Reports automatically include meaningful titles based on the report type
2. **Report Context Information**: Information about the query, configuration, and other relevant details
3. **Styled Tables**: Properly formatted tables with sortable columns (when applicable)
4. **Responsive Design**: Reports work well on desktop and mobile devices
5. **Timestamps**: Each report includes a generation timestamp

## Command Classes Using HTML Formatter

The following command classes use the HTML formatter:

- Query commands (`query execute`, `query interactive`)
- NLQ commands (`nlq query`)
- Object commands (`object list`, `object find`)
- Policy commands (`policy list`, `policy filter`)

## Customizing HTML Output

### For Command Implementers

When implementing a new command that will support HTML output, use the `CommandBase.format_output` method and provide relevant context information:

```python
from panflow.cli.command_base import CommandBase

# Later in your code
CommandBase.format_output(
    data=results,                      # The data to format (required)
    output_format="html",              # The output format (required)
    output_file="path/to/output.html", # Output file (optional)
    table_title="My Report Title",     # Basic title (optional)
    report_type="Security Policy",     # The type of report (optional)
    query_text="SELECT * FROM...",     # Original query text if applicable (optional)
    config_file="path/to/config.xml",  # Path to the configuration file used (optional)
    additional_info={                  # Additional information to include (optional)
        "Context": "vsys1",
        "Device Type": "firewall"
    }
)
```

### Extending the HTML Formatter

The HTML formatter is implemented in `panflow.cli.command_base.CommandBase.format_output`. If you need to extend the formatter with new features:

1. Edit the `format_output` method in `command_base.py`
2. Add any new CSS styles in the HTML template section
3. Update the data processing logic as needed

## Command-specific Report Formats

Different commands generate specialized HTML reports:

### Query Commands

Query commands generate reports with:
- The original query text
- Configuration file information
- Result tables based on the query result structure

### NLQ Commands

NLQ commands generate reports with:
- The original natural language query
- Detected intent and entities
- Results in an appropriate format based on the intent

### Policy and Object Commands

Policy and object commands generate reports with:
- Configuration context information
- Object/policy details with appropriate formatting
- Related metrics and statistics when available

## Using the Report Information Section

The Report Information section adds valuable context to HTML reports. When calling `format_output`, provide as much context as possible:

```python
CommandBase.format_output(
    data=results,
    output_format="html",
    output_file=output_file,
    report_type="Address Objects",
    query_text="MATCH (a:address) RETURN a.name, a.value",
    config_file="config.xml",
    additional_info={
        "Context": "vsys1",
        "Device Type": "firewall",
        "Operation": "list"
    }
)
```

This ensures reports are self-documenting and provide users with all the information they need to understand the report contents.