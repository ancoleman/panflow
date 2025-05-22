# PANFlow Documentation

Welcome to the PANFlow documentation! PANFlow is a comprehensive CLI tool and Python library for working with Palo Alto Networks PAN-OS XML configurations, supporting both Panorama and firewall configurations across multiple PAN-OS versions (10.1, 10.2, 11.0, 11.1, 11.2).

## 🚀 Quick Start

### Installation
```bash
pip install panflow
```

### Basic Usage
```bash
# List all address objects
panflow object list --config firewall.xml --type address

# Find duplicate objects
panflow deduplicate find --config panorama.xml --type service

# Query configurations with graph queries
panflow query execute --config config.xml --query "MATCH (a:address) WHERE a.name CONTAINS 'web' RETURN a.name, a.value"

# Natural language queries
panflow nlq query "show me all disabled security rules" --config config.xml --format html --report-file report.html
```

## 📚 Core Documentation

### Getting Started
- **[Getting Started Guide](getting_started.md)**: Installation, basic usage, and first steps
- **[CLI Reference](cli_reference.md)**: Comprehensive CLI command documentation
- **[Project Structure](directory_structure.md)**: Complete project organization and architecture

### Core Features
- **[Graph Query System](graph_query_language.md)**: Powerful Cypher-like queries for configuration analysis
- **[Natural Language Queries (NLQ)](nlq.md)**: AI-powered natural language configuration queries
- **[Deduplication Engine](deduplication.md)**: Advanced duplicate object detection and merging
- **[Bulk Operations](bulk_policy_ops.md)**: Efficient multi-object and multi-policy operations
- **[Configuration Merging](object_merger.md)**: Merge configurations with conflict resolution

### Advanced Features
- **[XML Package System](xml_package.md)**: Consolidated XML manipulation framework
- **[Dynamic XPath Resolution](dynamic_xpath.md)**: Version-aware XPath handling
- **[Shell Completion](shell_completion.md)**: Bash/Zsh completion support
- **[HTML Reporting](html_formatter_usage.md)**: Professional HTML report generation

## 🎯 Use Case Guides

### Object Management
- **[Object Operations](api/objects.md)**: Managing address objects, service objects, and groups
- **[Object Cleanup](cleanup_detection.md)**: Finding and removing unused objects
- **[Object Deduplication](deduplication.md)**: Identifying and merging duplicate objects

### Policy Management  
- **[Policy Operations](api/policies.md)**: Working with security, NAT, and decryption rules
- **[Policy Bulk Updates](policy_bulk_update_capabilities.md)**: Efficient multi-policy operations
- **[Policy Analysis](reporting_consolidation.md)**: Security policy analysis and reporting

### Configuration Analysis
- **[Graph Queries](query_examples.md)**: Examples of configuration queries and analysis
- **[Reporting System](reporting_consolidation.md)**: Generate comprehensive configuration reports
- **[Performance Optimization](performance_optimization.md)**: Optimize PANFlow for large configurations

## 🛠️ Developer Resources

### API Documentation
- **[API Overview](api/index.md)**: Complete API reference
- **[XML Abstractions](api/xml_abstractions.md)**: XML manipulation utilities
- **[Unit Testing](api/unit_tests.md)**: Testing framework and examples

### Development Guides
- **[Migration Guide](migration_guide.md)**: Migrating between PANFlow versions
- **[Package Consolidation](package_consolidation_guide.md)**: Understanding the consolidated architecture
- **[CLI Command Patterns](cli_command_pattern.md)**: Developing new CLI commands
- **[Custom Templates](custom_templates.md)**: Creating custom HTML report templates

## 🔄 Migration and Compatibility

- **[LXML Migration Guide](lxml_migration_guide.md)**: Migrating from older XML handling
- **[CLI Migration Plan](cli_migration_plan.md)**: Command structure changes
- **[XPath Refactoring](xpath_refactor_research.md)**: XPath system improvements

## 📋 Planning and Roadmap

- **[Visualization Implementation Plan](visualization_implementation_plan.md)**: Future configuration visualization capabilities
- **[Reporting Enhancements Plan](reporting_enhancements_plan.md)**: Planned reporting improvements
- **[Code Consolidation](code_consolidation.md)**: Architecture consolidation efforts

## 🎨 User Interface

### CLI Interface
PANFlow provides a comprehensive command-line interface with:
- **Standardized commands**: Consistent patterns across all operations
- **Multiple output formats**: JSON, table, CSV, YAML, HTML, and text
- **Shell completion**: Bash and Zsh completion support
- **Interactive modes**: Interactive query sessions and guided workflows

### Natural Language Interface
- **AI-powered queries**: Process natural language commands
- **Intent recognition**: Understand user intentions and map to CLI commands
- **Multi-format output**: Generate reports in various formats from natural language

## 🚀 Recent Major Enhancements (2025)

### v0.3.5 - Documentation and Visualization Planning
- Enhanced project documentation with comprehensive structure guide
- Added visualization implementation roadmap with business use cases
- Fixed NLQ HTML report formatting for better user experience

### v0.3.4 - Graph Query System Fixes
- Fixed critical graph building issues for service port extraction
- Enhanced device group context assignment across all object types
- Improved Panorama configuration handling with auto-detection

### v0.3.3 - Reporting System Overhaul
- Implemented professional Jinja2 template-based HTML reporting
- Added responsive design with mobile/tablet support
- Enhanced context-aware duplicate objects reporting

### v0.3.0 - Python 3.12+ and NLQ Expansion
- Upgraded to Python 3.12+ compatibility
- Implemented comprehensive NLQ bulk operations
- Added NetworkX integration for advanced graph operations

## 📞 Support and Community

- **[Troubleshooting Guide](troubleshooting.md)**: Common issues and solutions
- **[Error Handling](error_handling.md)**: Understanding PANFlow exceptions
- **GitHub Issues**: Report bugs and request features
- **CLI Help**: Run `panflow --help` for command-specific help

## 🎯 Key Benefits

1. **🔍 Advanced Analysis**: Graph-based queries and natural language processing
2. **⚡ Efficiency**: Bulk operations and automated deduplication
3. **📊 Professional Reporting**: HTML reports with responsive design
4. **🔧 Flexibility**: Multiple output formats and extensible architecture  
5. **🎨 User-Friendly**: Both CLI and natural language interfaces
6. **📈 Scalability**: Optimized for large enterprise configurations
7. **🔒 Reliability**: Comprehensive error handling and validation

PANFlow transforms PAN-OS configuration management from manual, error-prone processes into automated, reliable, and insightful operations.