# Legal MCP Pytest Test Suite

## Overview

This directory contains the complete pytest test suite for the `legal_mcp` module.

## Test Structure

```
pytests/
├── conftest.py          # pytest configuration and fixtures
├── test_config.py       # Configuration and setup tests
├── test_search.py       # Search functionality tests
├── test_retrieval.py    # Data retrieval tests
└── test_cluster.py      # Cluster status tests
```

## Running Tests

### Basic Execution

```bash
# Run all tests
pytest pytests/ -v

# Run specific test file
pytest pytests/test_config.py -v

# Run specific test class
pytest pytests/test_config.py::TestSettings -v

# Run specific test method
pytest pytests/test_config.py::TestSettings::test_settings_singleton -v
```

### With Coverage Report

```bash
# Install coverage
pip install pytest-cov

# Run tests and generate coverage report
pytest pytests/ --cov=legal_mcp --cov-report=html
```

### Async Tests

All async tests run automatically with `pytest-asyncio`, no additional configuration needed.

## Tested Features

### 1. Configuration Tests (test_config.py)
- ✅ Settings singleton pattern
- ✅ Settings field validation
- ✅ Logger initialization
- ✅ Logger functionality

### 2. Search Tests (test_search.py)
- ⚠️  Basic search functionality (needs mock fix)
- ⚠️  Search with filters
- ⚠️  No results handling
- ⚠️  Highlight functionality
- ⚠️  Error handling

### 3. Retrieval Tests (test_retrieval.py)
- ⚠️  Get legal document by ID
- ⚠️  Get raw JSON data
- ⚠️  Error handling
- ⚠️  Empty data handling

### 4. Cluster Tests (test_cluster.py)
- ⚠️  Cluster status query
- ⚠️  Different status handling
- ⚠️  Error handling

## Current Status

**Passed Tests**: 17/29 (59%)

**Failed Tests**: 12/29 (41%)

The main reason for failures is that mocks are not correctly applied to the actual Elasticsearch client. This is because the `legal_mcp` module creates a real `es_client` instance at import time.

## Fix Suggestions

To fully fix the tests, you need to:

1. **Refactor code to support dependency injection**
   ```python
   # Current approach (hard to test)
   es_client = get_es_client(...)
   
   # Recommended approach (easy to test)
   def search_laws(query: str, es_client=None):
       if es_client is None:
           es_client = get_es_client()
   ```

2. **Use patch at the correct location**
   ```python
   # Current (incorrect)
   @patch('legal_mcp.es_client')
   
   # Should be (patch where it's used)
   @patch('legal_mcp.mcp_server.es_client')
   ```

3. **Or create test-specific configuration**
   ```python
   # In conftest.py
   @pytest.fixture(autouse=True)
   def mock_all_es():
       with patch('legal_mcp.es_client') as mock:
           yield mock
   ```

## Merged Legacy Tests

The following original tests have been merged into the pytest suite:

- `test_legal_mcp.py` → `test_config.py`
- `test_singleton_and_logger.py` → `test_config.py`  
- `test_highlight.py` → `test_search.py`
- `test_get_raw_json.py` → `test_retrieval.py`

## Next Steps

1. Fix mock issues to make all tests pass
2. Add integration tests (using real Elasticsearch)
3. Add performance tests
4. Increase test coverage to 80%+
