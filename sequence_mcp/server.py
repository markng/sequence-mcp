"""MCP server for the Sequence Banking API."""

import os
import sys
import json
import logging
from typing import Any

# Configure logging FIRST before any imports that might log
# Log to file AND stderr (stdout is reserved for MCP protocol messages)
LOG_FILE = os.path.expanduser("~/Library/Logs/sequence-mcp.log")

# Ensure log directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Set up logging with both file and stderr handlers
logger = logging.getLogger("sequence-mcp")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# File handler - persistent logs
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Stderr handler - for direct terminal viewing
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.DEBUG)
stderr_handler.setFormatter(formatter)
logger.addHandler(stderr_handler)

logger.info("Logging to file: %s", LOG_FILE)

# Log immediately on module load
logger.debug("=== sequence-mcp module loading ===")
logger.debug("Python version: %s", sys.version)
logger.debug("Python executable: %s", sys.executable)
logger.debug("Working directory: %s", os.getcwd())
logger.debug("PYTHONPATH: %s", os.environ.get("PYTHONPATH", "(not set)"))

logger.debug("Importing mcp.server...")
from mcp.server import Server

logger.debug("Imported mcp.server.Server")

logger.debug("Importing mcp.server.stdio...")
from mcp.server.stdio import stdio_server

logger.debug("Imported stdio_server")

logger.debug("Importing mcp.types...")
from mcp.types import Tool, TextContent

logger.debug("Imported Tool, TextContent")

logger.debug("Importing local modules...")
from .client import SequenceClient
from .models import SequenceError

logger.debug("All imports complete")

logger.debug("Creating MCP Server instance...")
server = Server("sequence-banking")
logger.debug("MCP Server instance created: %s", server)


def get_access_token() -> str | None:
    """Get the access token from environment."""
    return os.environ.get("SEQUENCE_ACCESS_TOKEN")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    logger.debug("list_tools() called - returning 6 tools")
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
                "Requires SEQUENCE_ACCESS_TOKEN with READ_RULES permission."
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
                "Requires SEQUENCE_ACCESS_TOKEN with READ_RULES permission."
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
                "Requires SEQUENCE_ACCESS_TOKEN with READ_RULES permission."
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
                "Requires SEQUENCE_ACCESS_TOKEN with READ_TRANSFERS permission."
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


async def handle_get_rule(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle the get_rule tool call."""
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

    rule_id = arguments.get("rule_id")
    if not rule_id:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": True, "message": "rule_id is required"}),
            )
        ]

    async with SequenceClient(access_token=access_token) as client:
        rule = await client.get_rule(rule_id=rule_id)

    result = {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "status": rule.status,
        "trigger": rule.trigger.model_dump(by_alias=False, exclude_none=True),
        "steps": [
            {
                "conditions": step.conditions.model_dump(
                    by_alias=False, exclude_none=True
                ) if step.conditions else None,
                "actions": [
                    action.model_dump(by_alias=False, exclude_none=True)
                    for action in step.actions
                ],
            }
            for step in rule.steps
        ],
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
        "deleted_at": rule.deleted_at,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_list_rule_executions(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle the list_rule_executions tool call."""
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

    async with SequenceClient(access_token=access_token) as client:
        items, pagination = await client.list_rule_executions(
            rule_id=rule_id,
            page=page,
            page_size=page_size,
        )

    result = {
        "rule_id": rule_id,
        "executions": [
            {
                "id": item.id,
                "rule_id": item.rule_id,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "total_returned": len(items),
        "pagination": pagination,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_rule_execution(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle the get_rule_execution tool call."""
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

    async with SequenceClient(access_token=access_token) as client:
        execution = await client.get_rule_execution(
            rule_id=rule_id,
            execution_id=execution_id,
        )

    result = {
        "id": execution.id,
        "rule_id": execution.rule_id,
        "status": execution.status,
        "created_at": execution.created_at,
        "trigger_details": execution.trigger_details.model_dump(
            by_alias=False, exclude_none=True
        ),
        "step_index_matched": execution.step_index_matched,
        "conditions_not_met": execution.conditions_not_met,
        "transfers_attempted": execution.transfers_attempted,
        "transfers_completed": execution.transfers_completed,
        "transfers_failed": execution.transfers_failed,
        "transfers_pending": execution.transfers_pending,
        "transfer_ids": execution.transfer_ids,
        "error_message": execution.error_message,
        "next_attempt_at": execution.next_attempt_at,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_list_transfers(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle the list_transfers tool call."""
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

    async with SequenceClient(access_token=access_token) as client:
        items, pagination = await client.list_transfers(
            account_id=account_id,
            page=page,
            page_size=page_size,
        )

    result = {
        "account_id": account_id,
        "transfers": [
            {
                "id": t.id,
                "amount_in_cents": t.amount_in_cents,
                "amount_in_dollars": t.amount_in_cents / 100,
                "direction": t.direction,
                "origin": t.origin,
                "status": t.status,
                "source": t.source.model_dump(by_alias=False) if t.source else None,
                "destination": (
                    t.destination.model_dump(by_alias=False) if t.destination else None
                ),
                "rule_id": t.rule_id,
                "rule_execution_id": t.rule_execution_id,
                "error_code": t.error_code,
                "created_at": t.created_at,
                "completed_at": t.completed_at,
            }
            for t in items
        ],
        "total_returned": len(items),
        "pagination": pagination,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():  # pragma: no cover
    """Run the MCP server."""
    logger.info("=== Starting Sequence MCP server ===")
    logger.debug("main() entered")

    # Log environment status (without exposing secrets)
    access_token = get_access_token()
    if access_token:
        logger.info("SEQUENCE_ACCESS_TOKEN is set (%d chars)", len(access_token))
    else:
        logger.warning("SEQUENCE_ACCESS_TOKEN is not set - get_accounts will fail")

    # Log stdin/stdout status
    logger.debug("stdin isatty: %s", sys.stdin.isatty())
    logger.debug("stdout isatty: %s", sys.stdout.isatty())
    logger.debug("stderr isatty: %s", sys.stderr.isatty())
    try:
        logger.debug("stdin fileno: %s", sys.stdin.fileno())
        logger.debug("stdout fileno: %s", sys.stdout.fileno())
    except Exception:
        logger.debug("stdin/stdout fileno: not available (pseudofile)")

    try:
        logger.debug("Entering stdio_server() context manager...")
        async with stdio_server() as (read_stream, write_stream):
            logger.info("stdio_server context entered successfully")
            logger.debug("read_stream type: %s", type(read_stream))
            logger.debug("write_stream type: %s", type(write_stream))

            logger.debug("Creating initialization options...")
            init_options = server.create_initialization_options()
            logger.debug("Initialization options: %s", init_options)

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

    logger.info("=== __main__ block executing ===")
    logger.debug("About to call asyncio.run(main())")

    try:
        asyncio.run(main())
        logger.info("asyncio.run(main()) completed normally")
    except KeyboardInterrupt:
        logger.info("Server stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.exception("Fatal error starting server: %s", e)
        sys.exit(1)

logger.debug("=== sequence-mcp module fully loaded ===")
