"""Tests for the Sequence API client."""

import pytest
import httpx
import respx

from sequence_mcp.client import SequenceClient
from sequence_mcp.models import SequenceError


def describe_SequenceClient():  # noqa: C901
    """Tests for SequenceClient."""

    def describe_initialization():
        """Tests for client initialization."""

        def it_creates_client_with_access_token():
            client = SequenceClient(access_token="test_token")
            assert client.access_token == "test_token"
            assert client.timeout == 30.0

        def it_creates_client_with_custom_timeout():
            client = SequenceClient(access_token="test_token", timeout=60.0)
            assert client.timeout == 60.0

        def it_creates_client_without_access_token():
            client = SequenceClient()
            assert client.access_token is None

    def describe_get_accounts():
        """Tests for fetching accounts."""

        @pytest.mark.asyncio
        @respx.mock
        async def it_fetches_accounts_successfully(sample_accounts_response):
            respx.post("https://api.getsequence.io/accounts").mock(
                return_value=httpx.Response(200, json=sample_accounts_response)
            )

            async with SequenceClient(access_token="test_token") as client:
                accounts = await client.get_accounts()

            assert len(accounts) == 3
            assert accounts[0].id == "5579244"
            assert accounts[0].name == "Main Operating Pod"
            assert accounts[0].type == "Pod"
            assert accounts[0].balance.amount_in_dollars == 25342.77
            assert accounts[0].balance.error is None

        @pytest.mark.asyncio
        @respx.mock
        async def it_sends_correct_headers(sample_accounts_response):
            route = respx.post("https://api.getsequence.io/accounts").mock(
                return_value=httpx.Response(200, json=sample_accounts_response)
            )

            async with SequenceClient(access_token="my_secret_token") as client:
                await client.get_accounts()

            request = route.calls[0].request
            assert request.headers["x-sequence-access-token"] == "Bearer my_secret_token"
            assert request.headers["content-type"] == "application/json"

        @pytest.mark.asyncio
        async def it_raises_error_without_access_token():
            async with SequenceClient() as client:
                with pytest.raises(ValueError, match="Access token is required"):
                    await client.get_accounts()

        @pytest.mark.asyncio
        @respx.mock
        async def it_handles_unauthorized_error(sample_error_response_unauthorized):
            respx.post("https://api.getsequence.io/accounts").mock(
                return_value=httpx.Response(401, json=sample_error_response_unauthorized)
            )

            async with SequenceClient(access_token="invalid_token") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.get_accounts()

            assert exc_info.value.code == "INVALID_ACCESS_TOKEN"
            assert exc_info.value.message == "Unauthorized"
            assert exc_info.value.status_code == 401

        @pytest.mark.asyncio
        @respx.mock
        async def it_handles_accounts_with_balance_errors():
            response = {
                "message": "OK",
                "requestId": "test-123",
                "data": {
                    "accounts": [
                        {
                            "id": "123",
                            "name": "Test Account",
                            "balance": {
                                "amountInDollars": None,
                                "error": "Connection failed",
                            },
                            "type": "Account",
                        }
                    ],
                    "errors": [],
                },
            }
            respx.post("https://api.getsequence.io/accounts").mock(
                return_value=httpx.Response(200, json=response)
            )

            async with SequenceClient(access_token="test_token") as client:
                accounts = await client.get_accounts()

            assert len(accounts) == 1
            assert accounts[0].balance.amount_in_dollars is None
            assert accounts[0].balance.error == "Connection failed"

    def describe_trigger_rule():
        """Tests for triggering rules."""

        @pytest.mark.asyncio
        @respx.mock
        async def it_triggers_rule_successfully(sample_trigger_response):
            respx.post(
                "https://api.getsequence.io/remote-api/rules/ru_12345/trigger"
            ).mock(return_value=httpx.Response(200, json=sample_trigger_response))

            async with SequenceClient() as client:
                response = await client.trigger_rule(
                    rule_id="ru_12345",
                    api_secret="secret_123",
                )

            assert response.code == "OK"
            assert response.message == "Rule with id ru_12345 has been triggered"
            assert response.data.request_id == "b28f1d9e-8c2a-4d3e-9af1-XXXXXXXXXXXX"

        @pytest.mark.asyncio
        @respx.mock
        async def it_sends_correct_headers_for_rule_trigger(sample_trigger_response):
            route = respx.post(
                "https://api.getsequence.io/remote-api/rules/ru_test/trigger"
            ).mock(return_value=httpx.Response(200, json=sample_trigger_response))

            async with SequenceClient() as client:
                await client.trigger_rule(
                    rule_id="ru_test",
                    api_secret="my_rule_secret",
                )

            request = route.calls[0].request
            assert request.headers["x-sequence-signature"] == "Bearer my_rule_secret"
            assert request.headers["content-type"] == "application/json"

        @pytest.mark.asyncio
        @respx.mock
        async def it_includes_idempotency_key_when_provided(sample_trigger_response):
            route = respx.post(
                "https://api.getsequence.io/remote-api/rules/ru_test/trigger"
            ).mock(return_value=httpx.Response(200, json=sample_trigger_response))

            async with SequenceClient() as client:
                await client.trigger_rule(
                    rule_id="ru_test",
                    api_secret="secret",
                    idempotency_key="unique-key-123",
                )

            request = route.calls[0].request
            assert request.headers["idempotency-key"] == "unique-key-123"

        @pytest.mark.asyncio
        @respx.mock
        async def it_sends_payload_when_provided(sample_trigger_response):
            route = respx.post(
                "https://api.getsequence.io/remote-api/rules/ru_test/trigger"
            ).mock(return_value=httpx.Response(200, json=sample_trigger_response))

            async with SequenceClient() as client:
                await client.trigger_rule(
                    rule_id="ru_test",
                    api_secret="secret",
                    payload={"amount": 100, "note": "test"},
                )

            request = route.calls[0].request
            import json

            body = json.loads(request.content)
            assert body == {"amount": 100, "note": "test"}

        @pytest.mark.asyncio
        @respx.mock
        async def it_handles_invalid_api_secret(sample_error_response_invalid_secret):
            respx.post(
                "https://api.getsequence.io/remote-api/rules/ru_test/trigger"
            ).mock(
                return_value=httpx.Response(401, json=sample_error_response_invalid_secret)
            )

            async with SequenceClient() as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.trigger_rule(
                        rule_id="ru_test",
                        api_secret="wrong_secret",
                    )

            assert exc_info.value.code == "INVALID_API_SECRET"
            assert exc_info.value.status_code == 401

        @pytest.mark.asyncio
        @respx.mock
        async def it_handles_rate_limit_error(sample_error_response_rate_limit):
            respx.post(
                "https://api.getsequence.io/remote-api/rules/ru_12345/trigger"
            ).mock(
                return_value=httpx.Response(429, json=sample_error_response_rate_limit)
            )

            async with SequenceClient() as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.trigger_rule(
                        rule_id="ru_12345",
                        api_secret="secret",
                    )

            assert exc_info.value.code == "TOO_MANY_REQUESTS"
            assert exc_info.value.status_code == 429

        @pytest.mark.asyncio
        @respx.mock
        async def it_handles_invalid_rule_id():
            respx.post(
                "https://api.getsequence.io/remote-api/rules/invalid/trigger"
            ).mock(
                return_value=httpx.Response(
                    400, json={"code": "INVALID_REQUEST", "message": "Invalid request"}
                )
            )

            async with SequenceClient() as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.trigger_rule(
                        rule_id="invalid",
                        api_secret="secret",
                    )

            assert exc_info.value.code == "INVALID_REQUEST"
            assert exc_info.value.status_code == 400

        @pytest.mark.asyncio
        @respx.mock
        async def it_handles_non_json_error_response():
            respx.post(
                "https://api.getsequence.io/remote-api/rules/ru_test/trigger"
            ).mock(
                return_value=httpx.Response(
                    500, content=b"Internal Server Error", headers={"content-type": "text/plain"}
                )
            )

            async with SequenceClient() as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.trigger_rule(
                        rule_id="ru_test",
                        api_secret="secret",
                    )

            assert exc_info.value.code == "HTTP_ERROR"
            assert "500" in exc_info.value.message
            assert exc_info.value.status_code == 500

    def describe_error_handling():
        """Tests for error response handling."""

        @pytest.mark.asyncio
        @respx.mock
        async def it_handles_non_json_error_responses():
            """When the API returns a non-JSON error (e.g., HTML error page), the client
            should still raise a SequenceError with an HTTP_ERROR code."""
            respx.post("https://api.getsequence.io/accounts").mock(
                return_value=httpx.Response(
                    502,
                    content=b"<html><body>Bad Gateway</body></html>",
                    headers={"content-type": "text/html"},
                )
            )

            async with SequenceClient(access_token="test_token") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.get_accounts()

            assert exc_info.value.code == "HTTP_ERROR"
            assert "502" in exc_info.value.message
            assert exc_info.value.status_code == 502

    def describe_context_manager():
        """Tests for async context manager behavior."""

        @pytest.mark.asyncio
        async def it_properly_closes_client():
            client = SequenceClient(access_token="test")
            async with client:
                assert client._client is not None
            assert client._client is None

        @pytest.mark.asyncio
        async def it_can_close_manually():
            client = SequenceClient(access_token="test")
            client._get_client()  # Initialize the internal client
            assert client._client is not None
            await client.close()
            assert client._client is None

        @pytest.mark.asyncio
        async def it_handles_exit_when_client_is_none():
            """Test __aexit__ when _client was never initialized."""
            client = SequenceClient(access_token="test")
            assert client._client is None
            # Manually call __aexit__ without __aenter__
            await client.__aexit__(None, None, None)
            assert client._client is None

        @pytest.mark.asyncio
        async def it_handles_close_when_client_is_none():
            """Test close() when _client was never initialized."""
            client = SequenceClient(access_token="test")
            assert client._client is None
            # Should not raise any errors
            await client.close()
            assert client._client is None
