# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Unofficial** MCP (Model Context Protocol) server that wraps the Sequence Banking API, enabling AI assistants to interact with Sequence financial accounts. Not affiliated with Sequence.

## Tool inventory

### Legacy tools (old Sequence API)
- `get_accounts` — fetch all account balances (Pods, Income Sources, external accounts)
- `trigger_rule` — invoke an automation rule using a per-rule API secret

### Tier 1 Platform v1 tools (read-only, `https://api.getsequence.io/platform/v1`)
- `get_rule(rule_id)` — fetch rule composition: trigger, steps, conditions, actions
- `list_rule_executions(rule_id, page?, page_size?)` — list rule firings newest-first
- `get_rule_execution(rule_id, execution_id)` — full detail for one firing: transfer counts, IDs, error
- `list_transfers(account_id, page?, page_size?)` — per-account transfer history

### Tiers 2 & 3 (not yet implemented)
- Tier 2: `list_rules`, `get_account`, upgrade `get_accounts` to v1
- Tier 3: `create_transfer` (write capability, needs guardrails)

## Development Commands

```bash
# Install dependencies (use dev for testing)
pip install -e ".[dev]"

# Run tests
pytest -v

# Run a single test file
pytest tests/test_client.py -v

# Run a specific test function
pytest tests/test_client.py::describe_SequenceClient::describe_get_accounts::it_fetches_accounts_successfully -v

# Run the MCP server
python -m sequence_mcp.server
```

## Architecture

**Three-layer design:**
1. `models.py` - Pydantic models for API request/response serialization (uses field aliases like `amountInDollars` → `amount_in_dollars`)
2. `client.py` - Async HTTP client (`SequenceClient`) using httpx with context manager support
3. `server.py` - MCP server that exposes tools and delegates to the client

**Authentication:** Three methods coexist:
- `SEQUENCE_ACCESS_TOKEN` — legacy access token for `get_accounts`; uses `x-sequence-access-token` header
- Per-rule API secrets passed as parameters for `trigger_rule` — uses `x-sequence-signature` header
- `SEQUENCE_V1_API_KEY` — Platform v1 Bearer token for all four Tier 1 tools; uses standard `Authorization: Bearer` header. Generate from Sequence dashboard: Settings → API Keys. Requires scopes `READ_RULES` (rules + executions) and/or `READ_TRANSFERS` (transfers).

**Important**: The old `SEQUENCE_ACCESS_TOKEN` does NOT work with Platform v1 endpoints. `SEQUENCE_V1_API_KEY` is a separate env var backed by a distinct key type. Both must be present to use the full toolset.

**Manual setup**: Add `SEQUENCE_V1_API_KEY=<key>` to `~/.claude.env` after generating the key.

**Error handling:** `SequenceError` exception carries API error codes. The legacy API uses flat error responses `{"code": ..., "message": ...}`. Platform v1 uses nested responses `{"requestId": ..., "error": {"code": ..., "message": ...}}`. The client handles both shapes via `_handle_error_response`.

## Testing

Tests use `pytest-describe` for BDD-style nested test organization. HTTP mocking is done with `respx`. Test files mirror source structure with shared fixtures in `conftest.py`.

Example test pattern:
```python
def describe_ClassName():
    def describe_method_name():
        @pytest.mark.asyncio
        @respx.mock
        async def it_does_something(fixture_name):
            # arrange, act, assert
```
