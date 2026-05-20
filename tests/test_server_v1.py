"""Tests for the four new Platform v1 MCP tool handlers."""

import json
import os

import pytest
import httpx
import respx

from sequence_mcp.server import (
    list_tools,
    call_tool,
    handle_get_rule,
    handle_list_rule_executions,
    handle_get_rule_execution,
    handle_list_transfers,
)
from sequence_mcp.client import PLATFORM_V1_BASE_URL

V1_BASE = PLATFORM_V1_BASE_URL

# Test IDs matching conftest fixtures
RULE_ID = "551ff9b6-ddf1-4110-b611-1b11044b72d4"
EXECUTION_ID_1 = "4306b3e8-6e77-4c08-ab0b-bb33654af44c"
ACCOUNT_ID = "c7a7f26f-2ca5-4ae5-825a-70260591247c"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_token(monkeypatch, token: str = "test_token") -> None:
    monkeypatch.setenv("SEQUENCE_ACCESS_TOKEN", token)


def _clear_token(monkeypatch) -> None:
    monkeypatch.delenv("SEQUENCE_ACCESS_TOKEN", raising=False)


# ---------------------------------------------------------------------------
# list_tools — confirm four new tools are registered
# ---------------------------------------------------------------------------


def describe_list_tools_v1():
    """Tests that the four new tools are registered."""

    @pytest.mark.asyncio
    async def it_returns_six_tools():
        tools = await list_tools()
        assert len(tools) == 6

    @pytest.mark.asyncio
    async def it_includes_get_rule():
        tools = await list_tools()
        assert any(t.name == "get_rule" for t in tools)

    @pytest.mark.asyncio
    async def it_includes_list_rule_executions():
        tools = await list_tools()
        assert any(t.name == "list_rule_executions" for t in tools)

    @pytest.mark.asyncio
    async def it_includes_get_rule_execution():
        tools = await list_tools()
        assert any(t.name == "get_rule_execution" for t in tools)

    @pytest.mark.asyncio
    async def it_includes_list_transfers():
        tools = await list_tools()
        assert any(t.name == "list_transfers" for t in tools)

    @pytest.mark.asyncio
    async def it_get_rule_requires_rule_id():
        tools = await list_tools()
        get_rule = next(t for t in tools if t.name == "get_rule")
        assert "rule_id" in get_rule.inputSchema["required"]

    @pytest.mark.asyncio
    async def it_list_rule_executions_requires_rule_id():
        tools = await list_tools()
        tool = next(t for t in tools if t.name == "list_rule_executions")
        assert "rule_id" in tool.inputSchema["required"]
        # page and page_size are optional
        assert "page" not in tool.inputSchema.get("required", [])
        assert "page_size" not in tool.inputSchema.get("required", [])

    @pytest.mark.asyncio
    async def it_get_rule_execution_requires_rule_id_and_execution_id():
        tools = await list_tools()
        tool = next(t for t in tools if t.name == "get_rule_execution")
        assert "rule_id" in tool.inputSchema["required"]
        assert "execution_id" in tool.inputSchema["required"]

    @pytest.mark.asyncio
    async def it_list_transfers_requires_account_id():
        tools = await list_tools()
        tool = next(t for t in tools if t.name == "list_transfers")
        assert "account_id" in tool.inputSchema["required"]


# ---------------------------------------------------------------------------
# handle_get_rule
# ---------------------------------------------------------------------------


def describe_handle_get_rule():
    """Tests for handle_get_rule."""

    @pytest.mark.asyncio
    async def it_returns_error_when_token_not_set(monkeypatch):
        _clear_token(monkeypatch)
        result = await handle_get_rule({"rule_id": RULE_ID})
        data = json.loads(result[0].text)
        assert data["error"] is True
        assert "SEQUENCE_ACCESS_TOKEN" in data["message"]

    @pytest.mark.asyncio
    async def it_returns_error_when_rule_id_missing(monkeypatch):
        _set_token(monkeypatch)
        result = await handle_get_rule({})
        data = json.loads(result[0].text)
        assert data["error"] is True
        assert "rule_id" in data["message"]

    @pytest.mark.asyncio
    @respx.mock
    async def it_returns_rule_data(monkeypatch, sample_rule_response):
        _set_token(monkeypatch)
        respx.get(f"{V1_BASE}/rules/{RULE_ID}").mock(
            return_value=httpx.Response(200, json=sample_rule_response)
        )

        result = await handle_get_rule({"rule_id": RULE_ID})
        data = json.loads(result[0].text)

        assert data["id"] == RULE_ID
        assert data["name"] == "Auto-save on deposit"
        assert data["status"] == "ENABLED"
        assert data["trigger"]["type"] == "ON_FUNDS_TRANSFERRED"
        assert len(data["steps"]) == 1
        assert data["steps"][0]["actions"][0]["type"] == "PERCENTAGE"

    @pytest.mark.asyncio
    @respx.mock
    async def it_surfaces_api_error_via_call_tool(
        monkeypatch, sample_error_response_not_found
    ):
        _set_token(monkeypatch)
        respx.get(f"{V1_BASE}/rules/{RULE_ID}").mock(
            return_value=httpx.Response(404, json=sample_error_response_not_found)
        )

        result = await call_tool("get_rule", {"rule_id": RULE_ID})
        data = json.loads(result[0].text)

        assert data["error"] is True
        assert data["code"] == "NOT_FOUND"
        assert data["status_code"] == 404

    @pytest.mark.asyncio
    @respx.mock
    async def it_surfaces_rate_limit_error_via_call_tool(
        monkeypatch, sample_error_response_rate_limit
    ):
        _set_token(monkeypatch)
        respx.get(f"{V1_BASE}/rules/{RULE_ID}").mock(
            return_value=httpx.Response(429, json=sample_error_response_rate_limit)
        )

        result = await call_tool("get_rule", {"rule_id": RULE_ID})
        data = json.loads(result[0].text)

        assert data["error"] is True
        assert data["code"] == "TOO_MANY_REQUESTS"
        assert data["status_code"] == 429


# ---------------------------------------------------------------------------
# handle_list_rule_executions
# ---------------------------------------------------------------------------


def describe_handle_list_rule_executions():
    """Tests for handle_list_rule_executions."""

    @pytest.mark.asyncio
    async def it_returns_error_when_token_not_set(monkeypatch):
        _clear_token(monkeypatch)
        result = await handle_list_rule_executions({"rule_id": RULE_ID})
        data = json.loads(result[0].text)
        assert data["error"] is True
        assert "SEQUENCE_ACCESS_TOKEN" in data["message"]

    @pytest.mark.asyncio
    async def it_returns_error_when_rule_id_missing(monkeypatch):
        _set_token(monkeypatch)
        result = await handle_list_rule_executions({})
        data = json.loads(result[0].text)
        assert data["error"] is True
        assert "rule_id" in data["message"]

    @pytest.mark.asyncio
    @respx.mock
    async def it_returns_executions_list(
        monkeypatch, sample_list_rule_executions_response
    ):
        _set_token(monkeypatch)
        respx.get(f"{V1_BASE}/rules/{RULE_ID}/executions").mock(
            return_value=httpx.Response(
                200, json=sample_list_rule_executions_response
            )
        )

        result = await handle_list_rule_executions({"rule_id": RULE_ID})
        data = json.loads(result[0].text)

        assert data["rule_id"] == RULE_ID
        assert len(data["executions"]) == 2
        assert data["total_returned"] == 2
        assert data["executions"][0]["id"] == EXECUTION_ID_1
        assert data["executions"][0]["status"] == "EXECUTED"
        assert data["pagination"]["page"] == 1

    @pytest.mark.asyncio
    @respx.mock
    async def it_passes_page_and_page_size(
        monkeypatch, sample_list_rule_executions_response
    ):
        _set_token(monkeypatch)
        route = respx.get(f"{V1_BASE}/rules/{RULE_ID}/executions").mock(
            return_value=httpx.Response(
                200, json=sample_list_rule_executions_response
            )
        )

        await handle_list_rule_executions(
            {"rule_id": RULE_ID, "page": 2, "page_size": 25}
        )

        request = route.calls[0].request
        assert "page=2" in str(request.url)
        assert "pageSize=25" in str(request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def it_surfaces_401_via_call_tool(
        monkeypatch, sample_error_response_unauthorized
    ):
        _set_token(monkeypatch, "bad")
        respx.get(f"{V1_BASE}/rules/{RULE_ID}/executions").mock(
            return_value=httpx.Response(
                401, json=sample_error_response_unauthorized
            )
        )

        result = await call_tool("list_rule_executions", {"rule_id": RULE_ID})
        data = json.loads(result[0].text)

        assert data["error"] is True
        assert data["status_code"] == 401

    @pytest.mark.asyncio
    @respx.mock
    async def it_surfaces_429_via_call_tool(
        monkeypatch, sample_error_response_rate_limit
    ):
        _set_token(monkeypatch)
        respx.get(f"{V1_BASE}/rules/{RULE_ID}/executions").mock(
            return_value=httpx.Response(429, json=sample_error_response_rate_limit)
        )

        result = await call_tool("list_rule_executions", {"rule_id": RULE_ID})
        data = json.loads(result[0].text)

        assert data["error"] is True
        assert data["code"] == "TOO_MANY_REQUESTS"


# ---------------------------------------------------------------------------
# handle_get_rule_execution
# ---------------------------------------------------------------------------


def describe_handle_get_rule_execution():
    """Tests for handle_get_rule_execution."""

    @pytest.mark.asyncio
    async def it_returns_error_when_token_not_set(monkeypatch):
        _clear_token(monkeypatch)
        result = await handle_get_rule_execution(
            {"rule_id": RULE_ID, "execution_id": EXECUTION_ID_1}
        )
        data = json.loads(result[0].text)
        assert data["error"] is True
        assert "SEQUENCE_ACCESS_TOKEN" in data["message"]

    @pytest.mark.asyncio
    async def it_returns_error_when_rule_id_missing(monkeypatch):
        _set_token(monkeypatch)
        result = await handle_get_rule_execution({"execution_id": EXECUTION_ID_1})
        data = json.loads(result[0].text)
        assert data["error"] is True
        assert "rule_id" in data["message"]

    @pytest.mark.asyncio
    async def it_returns_error_when_execution_id_missing(monkeypatch):
        _set_token(monkeypatch)
        result = await handle_get_rule_execution({"rule_id": RULE_ID})
        data = json.loads(result[0].text)
        assert data["error"] is True
        assert "execution_id" in data["message"]

    @pytest.mark.asyncio
    @respx.mock
    async def it_returns_full_execution_detail(
        monkeypatch, sample_get_rule_execution_response
    ):
        _set_token(monkeypatch)
        respx.get(
            f"{V1_BASE}/rules/{RULE_ID}/executions/{EXECUTION_ID_1}"
        ).mock(
            return_value=httpx.Response(200, json=sample_get_rule_execution_response)
        )

        result = await handle_get_rule_execution(
            {"rule_id": RULE_ID, "execution_id": EXECUTION_ID_1}
        )
        data = json.loads(result[0].text)

        assert data["id"] == EXECUTION_ID_1
        assert data["rule_id"] == RULE_ID
        assert data["status"] == "EXECUTED"
        assert data["transfers_completed"] == 2
        assert data["transfers_failed"] == 0
        assert data["conditions_not_met"] is False
        assert data["step_index_matched"] == 0
        assert len(data["transfer_ids"]) == 2
        assert data["error_message"] is None
        assert data["trigger_details"]["type"] == "ON_FUNDS_TRANSFERRED"
        assert data["trigger_details"]["amount_in_cents"] == 250000

    @pytest.mark.asyncio
    @respx.mock
    async def it_returns_failed_execution_detail(
        monkeypatch, sample_get_rule_execution_failed_response
    ):
        _set_token(monkeypatch)
        failed_id = "0d6195f3-c855-4cc0-b150-3364bf57d07d"
        respx.get(f"{V1_BASE}/rules/{RULE_ID}/executions/{failed_id}").mock(
            return_value=httpx.Response(
                200, json=sample_get_rule_execution_failed_response
            )
        )

        result = await handle_get_rule_execution(
            {"rule_id": RULE_ID, "execution_id": failed_id}
        )
        data = json.loads(result[0].text)

        assert data["status"] == "FAILED"
        assert data["transfers_failed"] == 1
        assert data["error_message"] == "Insufficient funds in source account."

    @pytest.mark.asyncio
    @respx.mock
    async def it_surfaces_404_via_call_tool(
        monkeypatch, sample_error_response_not_found
    ):
        _set_token(monkeypatch)
        respx.get(
            f"{V1_BASE}/rules/{RULE_ID}/executions/{EXECUTION_ID_1}"
        ).mock(
            return_value=httpx.Response(404, json=sample_error_response_not_found)
        )

        result = await call_tool(
            "get_rule_execution",
            {"rule_id": RULE_ID, "execution_id": EXECUTION_ID_1},
        )
        data = json.loads(result[0].text)

        assert data["error"] is True
        assert data["status_code"] == 404

    @pytest.mark.asyncio
    @respx.mock
    async def it_surfaces_401_via_call_tool(
        monkeypatch, sample_error_response_unauthorized
    ):
        _set_token(monkeypatch, "bad")
        respx.get(
            f"{V1_BASE}/rules/{RULE_ID}/executions/{EXECUTION_ID_1}"
        ).mock(
            return_value=httpx.Response(
                401, json=sample_error_response_unauthorized
            )
        )

        result = await call_tool(
            "get_rule_execution",
            {"rule_id": RULE_ID, "execution_id": EXECUTION_ID_1},
        )
        data = json.loads(result[0].text)

        assert data["error"] is True
        assert data["status_code"] == 401


# ---------------------------------------------------------------------------
# handle_list_transfers
# ---------------------------------------------------------------------------


def describe_handle_list_transfers():
    """Tests for handle_list_transfers."""

    @pytest.mark.asyncio
    async def it_returns_error_when_token_not_set(monkeypatch):
        _clear_token(monkeypatch)
        result = await handle_list_transfers({"account_id": ACCOUNT_ID})
        data = json.loads(result[0].text)
        assert data["error"] is True
        assert "SEQUENCE_ACCESS_TOKEN" in data["message"]

    @pytest.mark.asyncio
    async def it_returns_error_when_account_id_missing(monkeypatch):
        _set_token(monkeypatch)
        result = await handle_list_transfers({})
        data = json.loads(result[0].text)
        assert data["error"] is True
        assert "account_id" in data["message"]

    @pytest.mark.asyncio
    @respx.mock
    async def it_returns_transfers_with_dollars(
        monkeypatch, sample_list_transfers_response
    ):
        _set_token(monkeypatch)
        respx.get(f"{V1_BASE}/accounts/{ACCOUNT_ID}/transfers").mock(
            return_value=httpx.Response(200, json=sample_list_transfers_response)
        )

        result = await handle_list_transfers({"account_id": ACCOUNT_ID})
        data = json.loads(result[0].text)

        assert data["account_id"] == ACCOUNT_ID
        assert len(data["transfers"]) == 1
        t = data["transfers"][0]
        assert t["id"] == "809e5e0b-bb0b-49b2-867a-8b44d04d9179"
        assert t["amount_in_cents"] == 100000
        assert t["amount_in_dollars"] == 1000.0
        assert t["direction"] == "INTERNAL"
        assert t["status"] == "COMPLETE"
        assert t["source"]["name"] == "Main Payroll"
        assert t["destination"]["name"] == "Emergency Fund"
        assert t["rule_id"] == RULE_ID
        assert t["rule_execution_id"] == EXECUTION_ID_1
        assert data["total_returned"] == 1
        assert data["pagination"]["page"] == 1

    @pytest.mark.asyncio
    @respx.mock
    async def it_handles_null_source(
        monkeypatch, sample_list_transfers_no_source_response
    ):
        _set_token(monkeypatch)
        respx.get(f"{V1_BASE}/accounts/{ACCOUNT_ID}/transfers").mock(
            return_value=httpx.Response(
                200, json=sample_list_transfers_no_source_response
            )
        )

        result = await handle_list_transfers({"account_id": ACCOUNT_ID})
        data = json.loads(result[0].text)

        t = data["transfers"][0]
        assert t["source"] is None
        assert t["rule_id"] is None
        assert t["rule_execution_id"] is None

    @pytest.mark.asyncio
    @respx.mock
    async def it_passes_page_and_page_size(
        monkeypatch, sample_list_transfers_response
    ):
        _set_token(monkeypatch)
        route = respx.get(f"{V1_BASE}/accounts/{ACCOUNT_ID}/transfers").mock(
            return_value=httpx.Response(200, json=sample_list_transfers_response)
        )

        await handle_list_transfers(
            {"account_id": ACCOUNT_ID, "page": 2, "page_size": 50}
        )

        request = route.calls[0].request
        assert "page=2" in str(request.url)
        assert "pageSize=50" in str(request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def it_surfaces_401_via_call_tool(
        monkeypatch, sample_error_response_unauthorized
    ):
        _set_token(monkeypatch, "bad")
        respx.get(f"{V1_BASE}/accounts/{ACCOUNT_ID}/transfers").mock(
            return_value=httpx.Response(
                401, json=sample_error_response_unauthorized
            )
        )

        result = await call_tool("list_transfers", {"account_id": ACCOUNT_ID})
        data = json.loads(result[0].text)

        assert data["error"] is True
        assert data["status_code"] == 401

    @pytest.mark.asyncio
    @respx.mock
    async def it_surfaces_429_via_call_tool(
        monkeypatch, sample_error_response_rate_limit
    ):
        _set_token(monkeypatch)
        respx.get(f"{V1_BASE}/accounts/{ACCOUNT_ID}/transfers").mock(
            return_value=httpx.Response(429, json=sample_error_response_rate_limit)
        )

        result = await call_tool("list_transfers", {"account_id": ACCOUNT_ID})
        data = json.loads(result[0].text)

        assert data["error"] is True
        assert data["code"] == "TOO_MANY_REQUESTS"
