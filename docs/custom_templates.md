# Custom HTML Report Templates

This guide explains how to customize the HTML report templates used by PANFlow.

## Overview

PANFlow uses [Jinja2](https://jinja.palletsprojects.com/) templates to generate HTML reports. These templates are located in the `panflow/templates/reports` directory. You can customize these templates by:

1. Creating a custom templates directory
2. Copying and modifying the templates you want to customize
3. Passing your custom templates directory to the `EnhancedReportingEngine`

## Directory Structure

The default template structure is as follows:
```
panflow/templates/
├── reports/
│   ├── base.html                      # Base template with common structure
│   ├── custom_report.html             # Template for custom reports
│   ├── object_usage.html              # Template for object usage reports
│   ├── security_policy_analysis.html  # Template for security policy analysis
│   └── sections/                      # Reusable section templates
│       ├── object_section.html        # Object-related section templates
│       └── policy_section.html        # Policy-related section templates
```

## Creating Custom Templates

To customize the templates:

1. Create a directory for your custom templates (e.g., `/path/to/custom/templates`)
2. Copy the template files you want to customize from the default directory to your custom directory, maintaining the same structure
3. Modify the templates as needed

For example, to customize the security policy analysis report:

```bash
mkdir -p /path/to/custom/templates/reports
cp /path/to/panflow/templates/reports/security_policy_analysis.html /path/to/custom/templates/reports/
# Edit /path/to/custom/templates/reports/security_policy_analysis.html
```

## Using Custom Templates

When initializing the `EnhancedReportingEngine`, you can provide your custom templates directory:

```python
from panflow.core.reporting import EnhancedReportingEngine

# Initialize with custom templates
engine = EnhancedReportingEngine(
    tree,
    device_type,
    context_type,
    version,
    custom_templates_dir="/path/to/custom/templates",
    **kwargs
)

# Generate a report using your custom templates
analysis = engine.generate_security_policy_analysis(
    output_file="report.html",
    output_format="html"
)
```

## Template Inheritance

The templates use Jinja2's template inheritance. The base template (`base.html`) defines the overall structure with blocks that can be overridden by child templates:

- `title`: The page title
- `report_title`: The main heading
- `report_description`: Subheading with description
- `content`: The main content of the report
- `extra_styles`: Additional CSS styles
- `extra_scripts`: Additional JavaScript

## Available Template Variables

### Security Policy Analysis Report

- `analysis`: The complete analysis data
  - `summary`: Summary statistics
  - `policies`: Information about each policy
  - `categories`: Policies grouped by various categories
  - `statistics`: Statistical data
  - `visualization`: Visualization data (if enabled)
- `include_hit_counts`: Whether hit count data is included

### Object Usage Report

- `analysis`: The complete analysis data
  - `summary`: Summary statistics
  - `objects`: Information about each object
  - `usage`: Usage data
  - `statistics`: Statistical data
  - `categories`: Objects grouped by type/attributes
  - `visualization`: Visualization data (if enabled)

### Custom Report

- `report`: The complete report data
  - `name`: Report name
  - `description`: Report description
  - `sections`: Report sections

## Jinja2 Template Filters

The following custom filters are available in templates:

- `json_encode`: Convert an object to JSON (e.g., `{{ object|json_encode }}`)
- `format_date`: Format a date (e.g., `{{ date|format_date }}`)
- `format_number`: Format a number with commas (e.g., `{{ number|format_number }}`)

## Example: Adding Company Branding

Here's an example of customizing the base template to add company branding:

```html
{% extends "base.html" %}

{% block extra_styles %}
.company-header {
    background-color: #003366;
    padding: 10px;
    margin-bottom: 20px;
}
.company-logo {
    height: 40px;
}
{% endblock %}

{% block report_title %}
<div class="company-header">
    <img src="https://example.com/logo.png" alt="Company Logo" class="company-logo">
    <h1 class="mb-4 text-white">{{ super() }}</h1>
</div>
{% endblock %}
```

Save this file as `/path/to/custom/templates/reports/base.html` to override the default base template.