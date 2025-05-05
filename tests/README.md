# PANFlow Tests

This directory contains the test suite for the PANFlow project.

## Test Structure

- `unit/`: Unit tests for individual modules and components
  - `core/`: Tests for core functionality
    - `test_xml_utils.py`: Tests for basic XML utilities
    - `test_xml_builder.py`: Tests for XmlNode, XmlBuilder, and XPathBuilder classes
    - `test_xml_query.py`: Tests for XmlQuery class
    - `test_xml_diff.py`: Tests for XmlDiff class
    - `test_xml_cache.py`: Tests for XML caching functionality
    - `test_xpath_resolver.py`: Tests for XPath resolution
  - `modules/`: Tests for higher-level modules

- `integration/`: Integration tests that verify multiple components working together

- `fixtures/`: Test data and fixtures

## Running Tests

To run the entire test suite:

```bash
pytest
```

To run with coverage:

```bash
pytest --cov=panflow
```

To generate an HTML coverage report:

```bash
pytest --cov=panflow --cov-report=html
```

## Writing Tests

When writing new tests:

1. Follow the existing structure - place unit tests in the appropriate directory under `unit/`
2. Use fixtures from `conftest.py` when possible
3. Name test files with the `test_` prefix
4. Name test functions with the `test_` prefix
5. Include docstrings for all test functions

## Test Fixtures

Common test fixtures are defined in `conftest.py`. These include:

- `fixture_path`: Path to the fixtures directory
- `sample_xml_string`: A basic PAN-OS XML configuration string
- `sample_xml_element`: An XML element parsed from the sample string
- `sample_xml_tree`: An XML tree parsed from the sample string
- `panorama_xml_tree`: A minimal Panorama XML configuration tree
- `firewall_xml_tree`: A minimal firewall XML configuration tree
- `sample_xpath_mapping`: A sample XPath mapping dictionary

## Adding New Fixtures

To add a new fixture:

1. For simple fixtures, add them to `conftest.py`
2. For larger XML files, add them to the `fixtures/` directory
3. Add a fixture function in `conftest.py` that loads the file

## XML Abstraction Tests

The tests for the new XML abstraction classes cover:

- `XmlNode`: A wrapper for XML elements with a more Pythonic interface
- `XmlBuilder`: A fluent interface for building XML hierarchies
- `XPathBuilder`: A builder for XPath expressions
- `XmlQuery`: A jQuery-like query interface for XML
- `XmlDiff`: A tool for comparing XML elements and detecting differences
- `LRUCache`: A caching mechanism for improving performance

See `docs/api/unit_tests.md` for more information about the test coverage for XML abstractions.

## Integration Tests

Integration tests should:

1. Test complete workflows
2. Use temporary files when making modifications
3. Clean up any resources they create
4. Not modify any existing files in the fixtures directory

## Test Coverage

The project uses pytest-cov to track test coverage. The current coverage for the new XML abstraction classes is high (84-100%), but overall project coverage is around 19%.

To run tests with coverage reporting:

```bash
# Generate terminal coverage report
python -m pytest --cov=panflow tests/

# Generate HTML coverage report
python -m pytest --cov=panflow --cov-report=html tests/
```

The HTML report will be generated in the `htmlcov` directory. Open `htmlcov/index.html` in a browser to view it.

### XML Abstractions Test Coverage

The XML abstraction classes have high test coverage:

- `xml_builder.py`: 94% coverage
- `xml_cache.py`: 93% coverage
- `xml_diff.py`: 84% coverage
- `xml_query.py`: 89% coverage

Focus areas for improving overall coverage:

1. CLI commands and interface
2. Bulk operations
3. Deduplication functionality
4. Reporting functionality