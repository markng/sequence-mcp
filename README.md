# Sequence Banking MCP Server

[![CI](https://github.com/markng/sequence-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/markng/sequence-mcp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/markng/sequence-mcp/graph/badge.svg)](https://codecov.io/gh/markng/sequence-mcp)

> **⚠️ UNOFFICIAL:** This is an unofficial, community-built MCP server. It is not affiliated with, endorsed by, or supported by Sequence.

An MCP (Model Context Protocol) server that provides access to the [Sequence](https://getsequence.io) banking API. This allows AI assistants like Claude to interact with your Sequence accounts programmatically.

## Features

### Original tools (legacy API)
- **get_accounts**: Fetch all financial accounts (Pods, Income Sources, external accounts) with current balances
- **trigger_rule**: Invoke automation rules configured in Sequence using per-rule API secrets

### Tier 1 Platform v1 tools (read-only, high CFO value)
- **get_rule**: Fetch a rule's full composition — trigger type, steps, conditions, and actions
- **list_rule_executions**: List recent executions of a rule with status (EXECUTED/PARTIAL/FAILED/IN_PROGRESS)
- **get_rule_execution**: Get full detail for one firing — transfer counts, IDs, and error messages
- **list_transfers**: List per-account transfer history ordered newest first

## Requirements

- Python 3.10 or higher
- A Sequence account with the External API enabled
- Access token and/or rule API secrets from your Sequence dashboard

## Installation

1. Clone or download this repository

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the package:
   ```bash
   pip install -e .
   ```

4. For development (includes test dependencies):
   ```bash
   pip install -e ".[dev]"
   ```

## Configuration

### Getting Your Credentials

#### Legacy tools (`get_accounts`, `trigger_rule`)

1. **Enable the External API**: Go to Settings > Enable Remote API in your Sequence dashboard
2. **Generate an Access Token**: Navigate to Account Settings > Access Tokens. Used for `get_accounts`.
3. **Get Rule API Secrets**: Each Rule with "Remote API" trigger type has an API secret. Used for `trigger_rule`.

#### Tier 1 Platform v1 tools (`SEQUENCE_V1_API_KEY`)

1. **Create a Platform v1 API Key**: Go to Settings → API Keys in the Sequence dashboard and create a new key.
2. Grant the key the scopes it needs:
   - `READ_RULES` — for `get_rule`, `list_rule_executions`, `get_rule_execution`
   - `READ_TRANSFERS` — for `list_transfers`
3. Export the key as `SEQUENCE_V1_API_KEY`.

> **Note**: The old-format `SEQUENCE_ACCESS_TOKEN` does NOT work with Platform v1 endpoints. A distinct key from Settings → API Keys is required.

### Environment Variables

Both variables must be set to use the full toolset:

```bash
# Legacy tools: get_accounts
export SEQUENCE_ACCESS_TOKEN="your_legacy_access_token_here"

# Tier 1 Platform v1 tools: get_rule, list_rule_executions, get_rule_execution, list_transfers
export SEQUENCE_V1_API_KEY="your_platform_v1_api_key_here"
```

**Manual step for Mark:** add `SEQUENCE_V1_API_KEY=<key>` to `~/.claude.env` once you generate the key from the Sequence dashboard.

## Usage

### Running the MCP Server

```bash
source venv/bin/activate
python -m sequence_mcp.server
```

### Using with Claude Desktop

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sequence": {
      "command": "/path/to/sequence-mcp/venv/bin/python",
      "args": ["-m", "sequence_mcp.server"],
      "env": {
        "SEQUENCE_ACCESS_TOKEN": "your_access_token_here"
      }
    }
  }
}
```

Replace `/path/to/sequence-mcp` with the actual path to this project.

### Available Tools

#### get_accounts

Fetches all financial accounts with their current balances.

**Requirements**: Legacy `SEQUENCE_ACCESS_TOKEN` (old-format access token).

**Returns**: List of accounts with id, name, type, and balance information.

#### trigger_rule

Triggers an automation rule in Sequence using a per-rule API secret.

**Parameters**:
- `rule_id` (required): The ID of the rule to trigger (e.g., "ru_12345")
- `api_secret` (required): The per-rule API secret
- `payload` (optional): JSON object to send with the trigger
- `idempotency_key` (optional): Unique key to prevent duplicate triggers on retry

#### get_rule

Fetches a rule's full composition including all steps, conditions, and actions.

**Requirements**: Platform v1 API key with `READ_RULES` scope.

**Parameters**:
- `rule_id` (required): UUID of the rule

#### list_rule_executions

Lists recent executions of a rule, newest first.

**Requirements**: Platform v1 API key with `READ_RULES` scope.

**Parameters**:
- `rule_id` (required): UUID of the rule
- `page` (optional, default 1): 1-based page index
- `page_size` (optional, default 10, max 100): Items per page

**Returns**: List of executions with id, status, created_at, and pagination metadata.

#### get_rule_execution

Gets full detail for a single rule execution.

**Requirements**: Platform v1 API key with `READ_RULES` scope.

**Parameters**:
- `rule_id` (required): UUID of the rule
- `execution_id` (required): UUID of the specific execution

**Returns**: Full execution detail including trigger type, step matched, transfer counts, transfer IDs, and error message.

#### list_transfers

Lists transfers for an account, newest first. Credit/debit card transactions are excluded by the API.

**Requirements**: Platform v1 API key with `READ_TRANSFERS` scope.

**Parameters**:
- `account_id` (required): UUID of the account
- `page` (optional, default 1): 1-based page index
- `page_size` (optional, default 10, max 100): Items per page

**Returns**: List of transfers with amount (cents and dollars), direction, origin, status, source/destination accounts, rule linkage, and timestamps.

## Development

### Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies (includes testing tools)
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage report
pytest --cov=sequence_mcp

# Run specific test file
pytest tests/test_client.py -v

# Run specific test function
pytest tests/test_client.py::describe_SequenceClient::describe_get_accounts -v
```

Tests use `pytest-describe` for BDD-style organization and `respx` for HTTP mocking.

### Project Structure

```
sequence-mcp/
├── sequence_mcp/
│   ├── __init__.py      # Package exports
│   ├── models.py        # Pydantic models for API responses
│   ├── client.py        # Async HTTP client for Sequence API
│   └── server.py        # MCP server implementation
├── tests/
│   ├── conftest.py       # Shared test fixtures
│   ├── test_models.py    # Model tests
│   ├── test_client.py    # Client tests (legacy endpoints)
│   ├── test_client_v1.py # Client tests (Platform v1 endpoints)
│   ├── test_server.py    # Server tests (legacy tools)
│   └── test_server_v1.py # Server tests (Tier 1 Platform v1 tools)
├── pyproject.toml       # Project configuration
└── README.md
```

## API Reference

This MCP server wraps the Sequence External API. For full API documentation, see:
https://support.getsequence.io/hc/en-us/articles/42813911824019-API-Overview

### Error Codes

| Code | Description |
|------|-------------|
| `INVALID_ACCESS_TOKEN` | Access token is missing or invalid |
| `INVALID_API_SECRET` | Rule API secret is incorrect |
| `INVALID_REQUEST` | Rule ID not found or not configured for API triggers |
| `TOO_MANY_REQUESTS` | Rate limit exceeded, slow down requests |
| `UNEXPECTED_ERROR` | Server error, usually transient |

## Security Notes

- Keep your access tokens and API secrets secure
- Never expose credentials in client-side code
- Use environment variables or secure secret management
- Rotate tokens periodically
- All requests are made over HTTPS

## License

MIT
