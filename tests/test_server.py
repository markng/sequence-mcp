"""Tests for the MCP server."""

import json
import os

import pytest
import httpx
import respx
from unittest.mock import AsyncMock, patch

from sequence_mcp.server import (
    list_tools,
    call_tool,
    handle_get_accounts,
    handle_trigger_rule,
    main,
    get_access_token,
)


def describe_list_tools():
    """Tests for listing available tools."""

    @pytest.mark.asyncio
    async def it_returns_two_tools():
        tools = await list_tools()
        assert len(tools) == 2

    @pytest.mark.asyncio
    async def it_includes_get_accounts_tool():
        tools = await list_tools()
        tool_names = [t.name for t in tools]
        assert "get_accounts" in tool_names

    @pytest.mark.asyncio
    async def it_includes_trigger_rule_tool():
        tools = await list_tools()
        tool_names = [t.name for t in tools]
        assert "trigger_rule" in tool_names

    @pytest.mark.asyncio
    async def it_has_correct_schema_for_get_accounts():
        tools = await list_tools()
        get_accounts = next(t for t in tools if t.name == "get_accounts")
        assert get_accounts.inputSchema["type"] == "object"
        assert get_accounts.inputSchema["required"] == []

    @pytest.mark.asyncio
    async def it_has_correct_schema_for_trigger_rule():
        tools = await list_tools()
        trigger_rule = next(t for t in tools if t.name == "trigger_rule")
        assert trigger_rule.inputSchema["type"] == "object"
        assert "rule_id" in trigger_rule.inputSchema["properties"]
        assert "api_secret" in trigger_rule.inputSchema["properties"]
        assert "rule_id" in trigger_rule.inputSchema["required"]
        assert "api_secret" in trigger_rule.inputSchema["required"]


def describe_call_tool():
    """Tests for the call_tool dispatcher."""

    @pytest.mark.asyncio
    async def it_returns_error_for_unknown_tool():
        result = await call_tool("unknown_tool", {})
        assert len(result) == 1
        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_exceptions_gracefully():
        # Call get_accounts without token set
        original_token = os.environ.get("SEQUENCE_ACCESS_TOKEN")
        if "SEQUENCE_ACCESS_TOKEN" in os.environ:
            del os.environ["SEQUENCE_ACCESS_TOKEN"]

        try:
            result = await call_tool("get_accounts", {})
            data = json.loads(result[0].text)
            assert data["error"] is True
            assert "SEQUENCE_ACCESS_TOKEN" in data["message"]
        finally:
            if original_token:
                os.environ["SEQUENCE_ACCESS_TOKEN"] = original_token

    @pytest.mark.asyncio
    async def it_handles_unexpected_exceptions(monkeypatch):
        """When an unexpected exception (not SequenceError) occurs, the server
        should catch it and return a JSON error response."""
        from sequence_mcp import server

        async def mock_handle_get_accounts():
            raise RuntimeError("Unexpected internal error")

        monkeypatch.setattr(server, "handle_get_accounts", mock_handle_get_accounts)

        result = await call_tool("get_accounts", {})
        data = json.loads(result[0].text)

        assert data["error"] is True
        assert "Unexpected internal error" in data["message"]


def describe_handle_get_accounts():
    """Tests for the get_accounts handler."""

    @pytest.mark.asyncio
    async def it_returns_error_when_token_not_set():
        original_token = os.environ.get("SEQUENCE_ACCESS_TOKEN")
        if "SEQUENCE_ACCESS_TOKEN" in os.environ:
            del os.environ["SEQUENCE_ACCESS_TOKEN"]

        try:
            result = await handle_get_accounts()
            data = json.loads(result[0].text)
            assert data["error"] is True
            assert "SEQUENCE_ACCESS_TOKEN" in data["message"]
        finally:
            if original_token:
                os.environ["SEQUENCE_ACCESS_TOKEN"] = original_token

    @pytest.mark.asyncio
    @respx.mock
    async def it_returns_accounts_when_successful(sample_accounts_response):
        respx.post("https://api.getsequence.io/accounts").mock(
            return_value=httpx.Response(200, json=sample_accounts_response)
        )

        original_token = os.environ.get("SEQUENCE_ACCESS_TOKEN")
        os.environ["SEQUENCE_ACCESS_TOKEN"] = "test_token"

        try:
            result = await handle_get_accounts()
            data = json.loads(result[0].text)
            assert "accounts" in data
            assert data["total_accounts"] == 3
            assert data["accounts"][0]["name"] == "Main Operating Pod"
            assert data["accounts"][0]["balance_dollars"] == 25342.77
        finally:
            if original_token:
                os.environ["SEQUENCE_ACCESS_TOKEN"] = original_token
            else:
                del os.environ["SEQUENCE_ACCESS_TOKEN"]

    @pytest.mark.asyncio
    @respx.mock
    async def it_handles_api_errors(sample_error_response_unauthorized):
        respx.post("https://api.getsequence.io/accounts").mock(
            return_value=httpx.Response(401, json=sample_error_response_unauthorized)
        )

        original_token = os.environ.get("SEQUENCE_ACCESS_TOKEN")
        os.environ["SEQUENCE_ACCESS_TOKEN"] = "invalid_token"

        try:
            result = await call_tool("get_accounts", {})
            data = json.loads(result[0].text)
            assert data["error"] is True
            assert data["code"] == "INVALID_ACCESS_TOKEN"
        finally:
            if original_token:
                os.environ["SEQUENCE_ACCESS_TOKEN"] = original_token
            else:
                del os.environ["SEQUENCE_ACCESS_TOKEN"]


def describe_handle_trigger_rule():
    """Tests for the trigger_rule handler."""

    @pytest.mark.asyncio
    async def it_returns_error_when_rule_id_missing():
        result = await handle_trigger_rule({"api_secret": "secret"})
        data = json.loads(result[0].text)
        assert data["error"] is True
        assert "rule_id" in data["message"]

    @pytest.mark.asyncio
    async def it_returns_error_when_api_secret_missing():
        result = await handle_trigger_rule({"rule_id": "ru_123"})
        data = json.loads(result[0].text)
        assert data["error"] is True
        assert "api_secret" in data["message"]

    @pytest.mark.asyncio
    @respx.mock
    async def it_triggers_rule_successfully(sample_trigger_response):
        respx.post("https://api.getsequence.io/remote-api/rules/ru_12345/trigger").mock(
            return_value=httpx.Response(200, json=sample_trigger_response)
        )

        result = await handle_trigger_rule(
            {"rule_id": "ru_12345", "api_secret": "secret_123"}
        )
        data = json.loads(result[0].text)

        assert data["success"] is True
        assert data["code"] == "OK"
        assert data["request_id"] == "b28f1d9e-8c2a-4d3e-9af1-XXXXXXXXXXXX"

    @pytest.mark.asyncio
    @respx.mock
    async def it_passes_payload_to_api(sample_trigger_response):
        route = respx.post(
            "https://api.getsequence.io/remote-api/rules/ru_test/trigger"
        ).mock(return_value=httpx.Response(200, json=sample_trigger_response))

        await handle_trigger_rule(
            {
                "rule_id": "ru_test",
                "api_secret": "secret",
                "payload": {"custom": "data"},
            }
        )

        request = route.calls[0].request
        body = json.loads(request.content)
        assert body == {"custom": "data"}

    @pytest.mark.asyncio
    @respx.mock
    async def it_passes_idempotency_key_to_api(sample_trigger_response):
        route = respx.post(
            "https://api.getsequence.io/remote-api/rules/ru_test/trigger"
        ).mock(return_value=httpx.Response(200, json=sample_trigger_response))

        await handle_trigger_rule(
            {
                "rule_id": "ru_test",
                "api_secret": "secret",
                "idempotency_key": "my-unique-key",
            }
        )

        request = route.calls[0].request
        assert request.headers["idempotency-key"] == "my-unique-key"

    @pytest.mark.asyncio
    @respx.mock
    async def it_handles_api_errors(sample_error_response_invalid_secret):
        respx.post("https://api.getsequence.io/remote-api/rules/ru_test/trigger").mock(
            return_value=httpx.Response(401, json=sample_error_response_invalid_secret)
        )

        result = await call_tool(
            "trigger_rule", {"rule_id": "ru_test", "api_secret": "wrong"}
        )
        data = json.loads(result[0].text)

        assert data["error"] is True
        assert data["code"] == "INVALID_API_SECRET"
        assert data["status_code"] == 401


def describe_get_access_token():
    """Tests for the get_access_token helper function."""

    def it_returns_token_when_set():
        original_token = os.environ.get("SEQUENCE_ACCESS_TOKEN")
        os.environ["SEQUENCE_ACCESS_TOKEN"] = "test_token_value"

        try:
            token = get_access_token()
            assert token == "test_token_value"
        finally:
            if original_token:
                os.environ["SEQUENCE_ACCESS_TOKEN"] = original_token
            else:
                del os.environ["SEQUENCE_ACCESS_TOKEN"]

    def it_returns_none_when_not_set():
        original_token = os.environ.get("SEQUENCE_ACCESS_TOKEN")
        if "SEQUENCE_ACCESS_TOKEN" in os.environ:
            del os.environ["SEQUENCE_ACCESS_TOKEN"]

        try:
            token = get_access_token()
            assert token is None
        finally:
            if original_token:
                os.environ["SEQUENCE_ACCESS_TOKEN"] = original_token


def describe_main():
    """Tests for the main server function."""

    @pytest.mark.asyncio
    async def it_runs_server_with_access_token_set(monkeypatch):
        """When SEQUENCE_ACCESS_TOKEN is set, main logs it and runs the server."""
        monkeypatch.setenv("SEQUENCE_ACCESS_TOKEN", "test_token_12345")

        # Create mock streams
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()

        # Mock stdio_server to return our mock streams
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = (
            mock_read_stream,
            mock_write_stream,
        )
        mock_context_manager.__aexit__.return_value = None

        # Mock the server.run to complete immediately
        from sequence_mcp import server

        mock_server_run = AsyncMock()
        monkeypatch.setattr(server.server, "run", mock_server_run)

        with patch(
            "sequence_mcp.server.stdio_server", return_value=mock_context_manager
        ):
            await main()

        # Verify server.run was called with the mock streams
        mock_server_run.assert_called_once()
        call_args = mock_server_run.call_args
        assert call_args[0][0] == mock_read_stream
        assert call_args[0][1] == mock_write_stream

    @pytest.mark.asyncio
    async def it_runs_server_without_access_token(monkeypatch):
        """When SEQUENCE_ACCESS_TOKEN is not set, main logs a warning but still runs."""
        if "SEQUENCE_ACCESS_TOKEN" in os.environ:
            monkeypatch.delenv("SEQUENCE_ACCESS_TOKEN")

        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = (
            mock_read_stream,
            mock_write_stream,
        )
        mock_context_manager.__aexit__.return_value = None

        from sequence_mcp import server

        mock_server_run = AsyncMock()
        monkeypatch.setattr(server.server, "run", mock_server_run)

        with patch(
            "sequence_mcp.server.stdio_server", return_value=mock_context_manager
        ):
            await main()

        # Server should still run even without token
        mock_server_run.assert_called_once()

    @pytest.mark.asyncio
    async def it_propagates_server_errors(monkeypatch):
        """When the MCP server raises an exception, main propagates it."""
        monkeypatch.setenv("SEQUENCE_ACCESS_TOKEN", "test_token")

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.side_effect = RuntimeError(
            "Server connection failed"
        )

        with patch(
            "sequence_mcp.server.stdio_server", return_value=mock_context_manager
        ):
            with pytest.raises(RuntimeError, match="Server connection failed"):
                await main()


def describe_main_entry_point():
    """Tests for the __main__ entry point behavior.

    The __main__ block (lines 230-239) handles:
    1. Running asyncio.run(main())
    2. Catching KeyboardInterrupt for graceful shutdown
    3. Catching other exceptions and exiting with code 1
    """

    def it_runs_main_via_asyncio_run(monkeypatch):
        """When the module runs as __main__, it calls asyncio.run(main())."""
        import asyncio
        import runpy
        import warnings

        # Track that asyncio.run was called
        run_called = []

        def mock_asyncio_run(coro):
            run_called.append(coro)
            # Close the coroutine to avoid "never awaited" warnings
            coro.close()
            # Raise SystemExit to stop execution
            raise SystemExit(0)

        monkeypatch.setattr(asyncio, "run", mock_asyncio_run)

        # Suppress the runpy warning about module already in sys.modules
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            # Run the module as __main__
            try:
                runpy.run_module("sequence_mcp.server", run_name="__main__")
            except SystemExit:
                pass  # Expected - we raised it in mock

        assert len(run_called) == 1  # asyncio.run was called once

    def it_handles_keyboard_interrupt(monkeypatch, caplog):
        """When KeyboardInterrupt occurs, the server logs and exits cleanly."""
        import asyncio
        import runpy
        import logging
        import warnings

        def mock_asyncio_run(coro):
            # Close the coroutine to avoid warnings
            coro.close()
            raise KeyboardInterrupt()

        monkeypatch.setattr(asyncio, "run", mock_asyncio_run)

        # Capture log messages and suppress runpy warnings
        with caplog.at_level(logging.INFO):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                # Run the module - should handle KeyboardInterrupt gracefully
                try:
                    runpy.run_module("sequence_mcp.server", run_name="__main__")
                except SystemExit:
                    pass  # Not expected but acceptable

        # The KeyboardInterrupt handler logs "Server stopped by user"
        assert any(
            "stopped by user" in record.message.lower() for record in caplog.records
        )

    def it_exits_with_code_1_on_fatal_error(monkeypatch, caplog):
        """When a fatal error occurs, the server logs and exits with code 1."""
        import asyncio
        import runpy
        import logging
        import warnings

        def mock_asyncio_run(coro):
            # Close the coroutine to avoid warnings
            coro.close()
            raise RuntimeError("Simulated fatal error")

        monkeypatch.setattr(asyncio, "run", mock_asyncio_run)

        # Capture log messages and suppress runpy warnings
        with caplog.at_level(logging.ERROR):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                # Run the module - should catch the exception and exit with code 1
                exit_code = None
                try:
                    runpy.run_module("sequence_mcp.server", run_name="__main__")
                except SystemExit as e:
                    exit_code = e.code

        assert exit_code == 1

        # The exception handler logs the error
        assert any(
            "Fatal error" in record.message or "Simulated fatal error" in record.message
            for record in caplog.records
        )
