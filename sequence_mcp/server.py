"""MCP server for the Sequence Banking API."""

import io
import json
import logging
import os
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client import SequenceClient
from .models import SequenceError

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
# Log to file AND stderr (stdout is reserved for MCP protocol messages)
LOG_FILE = os.path.expanduser("~/Library/Logs/sequence-mcp.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logger = logging.getLogger("sequence-mcp")
logger.setLevel(logging.DEBUG)

_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

_file_handler = logging.FileHandler(LOG_FILE)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(_formatter)
logger.addHandler(_file_handler)

_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setLevel(logging.DEBUG)
_stderr_handler.setFormatter(_formatter)
logger.addHandler(_stderr_handler)

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------

server = Server("sequence-banking")


def get_access_token() -> str | None:
    """Get the legacy access token from environment."""
    return os.environ.get("SEQUENCE_ACCESS_TOKEN")


def get_v1_api_key() -> str | None:
    """Get the Platform v1 API key from environment."""
    return os.environ.get("SEQUENCE_V1_API_KEY")


def _check_fileno(stream: object, name: str) -> None:
    """Log the file descriptor number of *stream*, or note it is a pseudofile.

    Some test runners (e.g. pytest) replace stdin/stdout with pseudofile objects
    that do not support ``fileno()``.  We catch only ``io.UnsupportedOperation``
    so that genuine ``OSError`` failures still surface.
    """
    try:
        fd = stream.fileno()  # type: ignore[union-attr]
        logger.debug("%s fileno: %s", name, fd)
    except io.UnsupportedOperation:
        logger.debug("%s fileno: not available (pseudofile)", name)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_accounts",
            description=(
                "Fetch all financial accounts from Sequence with their current balances. "
                "Returns Pods, Income Sources, and external accounts with balance information. "
                "Requires SEQUENCE_ACCESS_TOKEN environment variable."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="trigger_rule",
            description=(
                "Trigger an automation rule in Sequence. "
                "Rules can automate financial workflows like transfers. "
                "Requires the rule ID and its associated API secret."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "rule_id": {
                        "type": "string",
                        "description": "The ID of the rule to trigger (e.g., 'ru_12345')",
                    },
                    "api_secret": {
                        "type": "string",
                        "description": "The API secret associated with this rule",
                    },
                    "payload": {
                        "type": "object",
                        "description": "Optional JSON payload to send with the trigger",
                        "default": {},
                    },
                    "idempotency_key": {
                        "type": "string",
                        "description": "Optional key to prevent duplicate triggers on retry",
                    },
                },
                "required": ["rule_id", "api_secret"],
            },
        ),
        Tool(
            name="get_rule",
            description=(
                "Fetch a Sequence automation rule by ID, including its full composition: "
                "trigger type, all steps, conditions, and actions. "
                "Useful for auditing rule logic without visiting the Sequence dashboard. "
                "Requires SEQUENCE_V1_API_KEY with READ_RULES permission."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "rule_id": {
                        "type": "string",
                        "description": "UUID of the rule to fetch",
                    },
                },
                "required": ["rule_id"],
            },
        ),
        Tool(
            name="list_rule_executions",
            description=(
                "List recent executions of a Sequence automation rule, newest first. "
                "Returns status (EXECUTED/PARTIAL/FAILED/IN_PROGRESS) and timestamps. "
                "Use get_rule_execution for full detail on a specific firing. "
                "Replaces manual UI inspection of rule history. "
                "Requires SEQUENCE_V1_API_KEY with READ_RULES permission."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "rule_id": {
                        "type": "string",
                        "description": "UUID of the rule whose executions to list",
                    },
                    "page": {
                        "type": "integer",
                        "description": "1-based page index (default: 1)",
                        "default": 1,
                        "minimum": 1,
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Items per page, max 100 (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["rule_id"],
            },
        ),
        Tool(
            name="get_rule_execution",
            description=(
                "Get full detail for a single rule execution: trigger type, which step "
                "matched, transfer counts (attempted/completed/failed/pending), transfer IDs, "
                "and any error message. "
                "Use after list_rule_executions to investigate a specific firing. "
                "Requires SEQUENCE_V1_API_KEY with READ_RULES permission."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "rule_id": {
                        "type": "string",
                        "description": "UUID of the rule",
                    },
                    "execution_id": {
                        "type": "string",
                        "description": "UUID of the specific execution",
                    },
                },
                "required": ["rule_id", "execution_id"],
            },
        ),
        Tool(
            name="list_transfers",
            description=(
                "List transfers for a Sequence account, newest first. "
                "Covers rule-triggered transfers, user-initiated transfers, direct deposits, "
                "and external pulls. Credit/debit card transactions are excluded by the API. "
                "Especially useful for Apple Card balance reconstruction when the feed is stale. "
                "Requires SEQUENCE_V1_API_KEY with READ_TRANSFERS permission."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "UUID of the account whose transfers to list",
                    },
                    "page": {
                        "type": "integer",
                        "description": "1-based page index (default: 1)",
                        "default": 1,
                        "minimum": 1,
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Items per page, max 100 (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["account_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    logger.info("Tool called: %s with arguments: %s", name, arguments)
    try:
        if name == "get_accounts":
            result = await handle_get_accounts()
        elif name == "trigger_rule":
            result = await handle_trigger_rule(arguments)
        elif name == "get_rule":
            result = await handle_get_rule(arguments)
        elif name == "list_rule_executions":
            result = await handle_list_rule_executions(arguments)
        elif name == "get_rule_execution":
            result = await handle_get_rule_execution(arguments)
        elif name == "list_transfers":
            result = await handle_list_transfers(arguments)
        else:
            logger.warning("Unknown tool requested: %s", name)
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        logger.debug("Tool %s completed successfully", name)
        return result
    except SequenceError as e:
        logger.error(
            "SequenceError in %s: code=%s, message=%s, status=%s",
            name,
            e.code,
            e.message,
            e.status_code,
        )
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": True,
                        "code": e.code,
                        "message": e.message,
                        "status_code": e.status_code,
                    }
                ),
            )
        ]
    except Exception as e:
        logger.exception("Unexpected error in tool %s: %s", name, e)
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": True, "message": str(e)}),
            )
        ]


async def handle_get_accounts() -> list[TextContent]:
    """Handle the get_accounts tool call."""
    access_token = get_access_token()
    if not access_token:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": True,
                        "message": "SEQUENCE_ACCESS_TOKEN environment variable is not set",
                    }
                ),
            )
        ]

    async with SequenceClient(access_token=access_token) as client:
        accounts = await client.get_accounts()

    result = {
        "accounts": [
            {
                "id": account.id,
                "name": account.name,
                "type": account.type,
                "balance_dollars": account.balance.amount_in_dollars,
                "balance_error": account.balance.error,
            }
            for account in accounts
        ],
        "total_accounts": len(accounts),
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_trigger_rule(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle the trigger_rule tool call."""
    rule_id = arguments.get("rule_id")
    api_secret = arguments.get("api_secret")
    payload = arguments.get("payload", {})
    idempotency_key = arguments.get("idempotency_key")

    if not rule_id:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": True, "message": "rule_id is required"}),
            )
        ]

    if not api_secret:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": True, "message": "api_secret is required"}),
            )
        ]

    async with SequenceClient() as client:
        response = await client.trigger_rule(
            rule_id=rule_id,
            api_secret=api_secret,
            payload=payload,
            idempotency_key=idempotency_key,
        )

    result = {
        "success": True,
        "code": response.code,
        "message": response.message,
        "request_id": response.data.request_id,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def _require_v1_api_key() -> str | None:
    """Return the Platform v1 API key, or None if unset.

    Callers are responsible for returning an appropriate error response when
    this returns None (so that the server handler can produce a user-visible
    error rather than raising during tool dispatch).
    """
    return get_v1_api_key()


async def handle_get_rule(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle the get_rule tool call."""
    v1_key = _require_v1_api_key()
    if not v1_key:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": True,
                        "message": (
                            "SEQUENCE_V1_API_KEY environment variable is not set. "
                            "Generate a Platform v1 API key from Sequence dashboard "
                            "(Settings > API Keys) with READ_RULES scope."
                        ),
                    }
                ),
            )
        ]

    rule_id = arguments.get("rule_id")
    if not rule_id:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": True, "message": "rule_id is required"}),
            )
        ]

    async with SequenceClient(access_token=v1_key) as client:
        rule = await client.get_rule(rule_id=rule_id)

    return [TextContent(type="text", text=json.dumps(rule.to_tool_payload(), indent=2))]


async def handle_list_rule_executions(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle the list_rule_executions tool call."""
    v1_key = _require_v1_api_key()
    if not v1_key:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": True,
                        "message": (
                            "SEQUENCE_V1_API_KEY environment variable is not set. "
                            "Generate a Platform v1 API key from Sequence dashboard "
                            "(Settings > API Keys) with READ_RULES scope."
                        ),
                    }
                ),
            )
        ]

    rule_id = arguments.get("rule_id")
    if not rule_id:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": True, "message": "rule_id is required"}),
            )
        ]

    page = arguments.get("page", 1)
    page_size = arguments.get("page_size", 10)

    async with SequenceClient(access_token=v1_key) as client:
        items, pagination = await client.list_rule_executions(
            rule_id=rule_id,
            page=page,
            page_size=page_size,
        )

    result = {
        "rule_id": rule_id,
        "executions": [item.to_tool_payload() for item in items],
        "total_returned": len(items),
        "pagination": pagination,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_rule_execution(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle the get_rule_execution tool call."""
    v1_key = _require_v1_api_key()
    if not v1_key:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": True,
                        "message": (
                            "SEQUENCE_V1_API_KEY environment variable is not set. "
                            "Generate a Platform v1 API key from Sequence dashboard "
                            "(Settings > API Keys) with READ_RULES scope."
                        ),
                    }
                ),
            )
        ]

    rule_id = arguments.get("rule_id")
    if not rule_id:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": True, "message": "rule_id is required"}),
            )
        ]

    execution_id = arguments.get("execution_id")
    if not execution_id:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": True, "message": "execution_id is required"}),
            )
        ]

    async with SequenceClient(access_token=v1_key) as client:
        execution = await client.get_rule_execution(
            rule_id=rule_id,
            execution_id=execution_id,
        )

    return [
        TextContent(type="text", text=json.dumps(execution.to_tool_payload(), indent=2))
    ]


async def handle_list_transfers(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle the list_transfers tool call."""
    v1_key = _require_v1_api_key()
    if not v1_key:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": True,
                        "message": (
                            "SEQUENCE_V1_API_KEY environment variable is not set. "
                            "Generate a Platform v1 API key from Sequence dashboard "
                            "(Settings > API Keys) with READ_TRANSFERS scope."
                        ),
                    }
                ),
            )
        ]

    account_id = arguments.get("account_id")
    if not account_id:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": True, "message": "account_id is required"}),
            )
        ]

    page = arguments.get("page", 1)
    page_size = arguments.get("page_size", 10)

    async with SequenceClient(access_token=v1_key) as client:
        items, pagination = await client.list_transfers(
            account_id=account_id,
            page=page,
            page_size=page_size,
        )

    result = {
        "account_id": account_id,
        "transfers": [t.to_tool_payload() for t in items],
        "total_returned": len(items),
        "pagination": pagination,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():  # pragma: no cover
    """Run the MCP server."""
    logger.info("=== Starting Sequence MCP server ===")

    # Log environment status (without exposing secrets)
    access_token = get_access_token()
    if access_token:
        logger.info("SEQUENCE_ACCESS_TOKEN is set (%d chars)", len(access_token))
    else:
        logger.warning("SEQUENCE_ACCESS_TOKEN is not set - get_accounts will fail")

    v1_key = get_v1_api_key()
    if v1_key:
        logger.info("SEQUENCE_V1_API_KEY is set (%d chars)", len(v1_key))
    else:
        logger.warning(
            "SEQUENCE_V1_API_KEY is not set - v1 tools (get_rule, list_rule_executions, "
            "get_rule_execution, list_transfers) will fail"
        )

    # Log stdin/stdout status
    logger.debug("stdin isatty: %s", sys.stdin.isatty())
    logger.debug("stdout isatty: %s", sys.stdout.isatty())
    logger.debug("stderr isatty: %s", sys.stderr.isatty())
    _check_fileno(sys.stdin, "stdin")
    _check_fileno(sys.stdout, "stdout")

    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("stdio_server context entered successfully")
            init_options = server.create_initialization_options()
            logger.info("Calling server.run() - awaiting MCP requests...")
            await server.run(
                read_stream,
                write_stream,
                init_options,
            )
            logger.info("server.run() returned normally")
    except Exception as e:
        logger.exception("MCP server error: %s", e)
        raise


if __name__ == "__main__":  # pragma: no cover
    import asyncio

    try:
        asyncio.run(main())
        logger.info("asyncio.run(main()) completed normally")
    except KeyboardInterrupt:
        logger.info("Server stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.exception("Fatal error starting server: %s", e)
        sys.exit(1)
