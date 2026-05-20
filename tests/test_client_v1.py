"""Tests for the Platform v1 client methods."""

import pytest
import httpx
import respx

from sequence_mcp.client import SequenceClient, PLATFORM_V1_BASE_URL
from sequence_mcp.models import SequenceError

V1_BASE = PLATFORM_V1_BASE_URL

# Test IDs matching conftest fixtures
RULE_ID = "551ff9b6-ddf1-4110-b611-1b11044b72d4"
EXECUTION_ID_1 = "4306b3e8-6e77-4c08-ab0b-bb33654af44c"
ACCOUNT_ID = "c7a7f26f-2ca5-4ae5-825a-70260591247c"


def describe_SequenceClient_v1():
    """Tests for Platform v1 client methods."""

    # ------------------------------------------------------------------
    # v1 auth header helper
    # ------------------------------------------------------------------

    def describe__v1_auth_headers():
        """Tests for _v1_auth_headers."""

        def it_returns_bearer_header_when_token_set():
            client = SequenceClient(access_token="tok_abc")
            headers = client._v1_auth_headers()
            assert headers["Authorization"] == "Bearer tok_abc"

        def it_raises_when_no_access_token():
            client = SequenceClient()
            with pytest.raises(ValueError, match="Access token is required"):
                client._v1_auth_headers()

    # ------------------------------------------------------------------
    # get_rule
    # ------------------------------------------------------------------

    def describe_get_rule():
        """Tests for get_rule."""

        @pytest.mark.asyncio
        @respx.mock
        async def it_fetches_rule_successfully(sample_rule_response):
            respx.get(f"{V1_BASE}/rules/{RULE_ID}").mock(
                return_value=httpx.Response(200, json=sample_rule_response)
            )

            async with SequenceClient(access_token="tok") as client:
                rule = await client.get_rule(rule_id=RULE_ID)

            assert rule.id == RULE_ID
            assert rule.name == "Auto-save on deposit"
            assert rule.status == "ENABLED"
            assert rule.trigger.type == "ON_FUNDS_TRANSFERRED"
            assert len(rule.steps) == 1
            assert rule.steps[0].actions[0].type == "PERCENTAGE"

        @pytest.mark.asyncio
        @respx.mock
        async def it_sends_bearer_auth_header(sample_rule_response):
            route = respx.get(f"{V1_BASE}/rules/{RULE_ID}").mock(
                return_value=httpx.Response(200, json=sample_rule_response)
            )

            async with SequenceClient(access_token="my_token") as client:
                await client.get_rule(rule_id=RULE_ID)

            request = route.calls[0].request
            assert request.headers["Authorization"] == "Bearer my_token"

        @pytest.mark.asyncio
        @respx.mock
        async def it_raises_on_404(sample_error_response_not_found):
            respx.get(f"{V1_BASE}/rules/{RULE_ID}").mock(
                return_value=httpx.Response(404, json=sample_error_response_not_found)
            )

            async with SequenceClient(access_token="tok") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.get_rule(rule_id=RULE_ID)

            assert exc_info.value.code == "NOT_FOUND"
            assert exc_info.value.status_code == 404

        @pytest.mark.asyncio
        @respx.mock
        async def it_raises_on_401(sample_error_response_unauthorized):
            respx.get(f"{V1_BASE}/rules/{RULE_ID}").mock(
                return_value=httpx.Response(
                    401, json=sample_error_response_unauthorized
                )
            )

            async with SequenceClient(access_token="bad_token") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.get_rule(rule_id=RULE_ID)

            assert exc_info.value.code == "INVALID_ACCESS_TOKEN"
            assert exc_info.value.status_code == 401

        @pytest.mark.asyncio
        @respx.mock
        async def it_raises_on_403(sample_error_response_forbidden):
            respx.get(f"{V1_BASE}/rules/{RULE_ID}").mock(
                return_value=httpx.Response(403, json=sample_error_response_forbidden)
            )

            async with SequenceClient(access_token="tok") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.get_rule(rule_id=RULE_ID)

            assert exc_info.value.code == "FORBIDDEN"
            assert exc_info.value.status_code == 403

        @pytest.mark.asyncio
        @respx.mock
        async def it_raises_on_429(sample_error_response_rate_limit):
            respx.get(f"{V1_BASE}/rules/{RULE_ID}").mock(
                return_value=httpx.Response(
                    429, json=sample_error_response_rate_limit
                )
            )

            async with SequenceClient(access_token="tok") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.get_rule(rule_id=RULE_ID)

            assert exc_info.value.code == "TOO_MANY_REQUESTS"
            assert exc_info.value.status_code == 429

        @pytest.mark.asyncio
        async def it_raises_value_error_without_token():
            async with SequenceClient() as client:
                with pytest.raises(ValueError, match="Access token is required"):
                    await client.get_rule(rule_id=RULE_ID)

    # ------------------------------------------------------------------
    # list_rule_executions
    # ------------------------------------------------------------------

    def describe_list_rule_executions():
        """Tests for list_rule_executions."""

        @pytest.mark.asyncio
        @respx.mock
        async def it_returns_executions_and_pagination(
            sample_list_rule_executions_response,
        ):
            respx.get(f"{V1_BASE}/rules/{RULE_ID}/executions").mock(
                return_value=httpx.Response(
                    200, json=sample_list_rule_executions_response
                )
            )

            async with SequenceClient(access_token="tok") as client:
                items, pagination = await client.list_rule_executions(rule_id=RULE_ID)

            assert len(items) == 2
            assert items[0].id == EXECUTION_ID_1
            assert items[0].status == "EXECUTED"
            assert items[1].status == "PARTIAL"
            assert pagination["page"] == 1
            assert pagination["pageSize"] == 10

        @pytest.mark.asyncio
        @respx.mock
        async def it_passes_page_and_page_size_as_query_params(
            sample_list_rule_executions_response,
        ):
            route = respx.get(f"{V1_BASE}/rules/{RULE_ID}/executions").mock(
                return_value=httpx.Response(
                    200, json=sample_list_rule_executions_response
                )
            )

            async with SequenceClient(access_token="tok") as client:
                await client.list_rule_executions(
                    rule_id=RULE_ID, page=2, page_size=25
                )

            request = route.calls[0].request
            assert "page=2" in str(request.url)
            assert "pageSize=25" in str(request.url)

        @pytest.mark.asyncio
        @respx.mock
        async def it_raises_on_401(sample_error_response_unauthorized):
            respx.get(f"{V1_BASE}/rules/{RULE_ID}/executions").mock(
                return_value=httpx.Response(
                    401, json=sample_error_response_unauthorized
                )
            )

            async with SequenceClient(access_token="bad") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.list_rule_executions(rule_id=RULE_ID)

            assert exc_info.value.status_code == 401

        @pytest.mark.asyncio
        @respx.mock
        async def it_raises_on_429(sample_error_response_rate_limit):
            respx.get(f"{V1_BASE}/rules/{RULE_ID}/executions").mock(
                return_value=httpx.Response(
                    429, json=sample_error_response_rate_limit
                )
            )

            async with SequenceClient(access_token="tok") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.list_rule_executions(rule_id=RULE_ID)

            assert exc_info.value.status_code == 429

        @pytest.mark.asyncio
        async def it_raises_value_error_without_token():
            async with SequenceClient() as client:
                with pytest.raises(ValueError):
                    await client.list_rule_executions(rule_id=RULE_ID)

    # ------------------------------------------------------------------
    # get_rule_execution
    # ------------------------------------------------------------------

    def describe_get_rule_execution():
        """Tests for get_rule_execution."""

        @pytest.mark.asyncio
        @respx.mock
        async def it_returns_full_execution_detail(
            sample_get_rule_execution_response,
        ):
            respx.get(
                f"{V1_BASE}/rules/{RULE_ID}/executions/{EXECUTION_ID_1}"
            ).mock(
                return_value=httpx.Response(
                    200, json=sample_get_rule_execution_response
                )
            )

            async with SequenceClient(access_token="tok") as client:
                execution = await client.get_rule_execution(
                    rule_id=RULE_ID, execution_id=EXECUTION_ID_1
                )

            assert execution.id == EXECUTION_ID_1
            assert execution.rule_id == RULE_ID
            assert execution.status == "EXECUTED"
            assert execution.transfers_completed == 2
            assert execution.transfers_failed == 0
            assert execution.conditions_not_met is False
            assert execution.step_index_matched == 0
            assert len(execution.transfer_ids) == 2
            assert execution.error_message is None
            assert execution.trigger_details.type == "ON_FUNDS_TRANSFERRED"
            assert execution.trigger_details.amount_in_cents == 250000

        @pytest.mark.asyncio
        @respx.mock
        async def it_handles_failed_execution(
            sample_get_rule_execution_failed_response,
        ):
            failed_exec_id = "0d6195f3-c855-4cc0-b150-3364bf57d07d"
            respx.get(
                f"{V1_BASE}/rules/{RULE_ID}/executions/{failed_exec_id}"
            ).mock(
                return_value=httpx.Response(
                    200, json=sample_get_rule_execution_failed_response
                )
            )

            async with SequenceClient(access_token="tok") as client:
                execution = await client.get_rule_execution(
                    rule_id=RULE_ID, execution_id=failed_exec_id
                )

            assert execution.status == "FAILED"
            assert execution.transfers_failed == 1
            assert execution.error_message == "Insufficient funds in source account."

        @pytest.mark.asyncio
        @respx.mock
        async def it_raises_on_404(sample_error_response_not_found):
            respx.get(
                f"{V1_BASE}/rules/{RULE_ID}/executions/{EXECUTION_ID_1}"
            ).mock(
                return_value=httpx.Response(404, json=sample_error_response_not_found)
            )

            async with SequenceClient(access_token="tok") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.get_rule_execution(
                        rule_id=RULE_ID, execution_id=EXECUTION_ID_1
                    )

            assert exc_info.value.status_code == 404

        @pytest.mark.asyncio
        @respx.mock
        async def it_raises_on_401(sample_error_response_unauthorized):
            respx.get(
                f"{V1_BASE}/rules/{RULE_ID}/executions/{EXECUTION_ID_1}"
            ).mock(
                return_value=httpx.Response(
                    401, json=sample_error_response_unauthorized
                )
            )

            async with SequenceClient(access_token="bad") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.get_rule_execution(
                        rule_id=RULE_ID, execution_id=EXECUTION_ID_1
                    )

            assert exc_info.value.status_code == 401

        @pytest.mark.asyncio
        @respx.mock
        async def it_raises_on_429(sample_error_response_rate_limit):
            respx.get(
                f"{V1_BASE}/rules/{RULE_ID}/executions/{EXECUTION_ID_1}"
            ).mock(
                return_value=httpx.Response(
                    429, json=sample_error_response_rate_limit
                )
            )

            async with SequenceClient(access_token="tok") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.get_rule_execution(
                        rule_id=RULE_ID, execution_id=EXECUTION_ID_1
                    )

            assert exc_info.value.status_code == 429

        @pytest.mark.asyncio
        async def it_raises_value_error_without_token():
            async with SequenceClient() as client:
                with pytest.raises(ValueError):
                    await client.get_rule_execution(
                        rule_id=RULE_ID, execution_id=EXECUTION_ID_1
                    )

    # ------------------------------------------------------------------
    # list_transfers
    # ------------------------------------------------------------------

    def describe_list_transfers():
        """Tests for list_transfers."""

        @pytest.mark.asyncio
        @respx.mock
        async def it_returns_transfers_and_pagination(
            sample_list_transfers_response,
        ):
            respx.get(f"{V1_BASE}/accounts/{ACCOUNT_ID}/transfers").mock(
                return_value=httpx.Response(200, json=sample_list_transfers_response)
            )

            async with SequenceClient(access_token="tok") as client:
                items, pagination = await client.list_transfers(
                    account_id=ACCOUNT_ID
                )

            assert len(items) == 1
            transfer = items[0]
            assert transfer.id == "809e5e0b-bb0b-49b2-867a-8b44d04d9179"
            assert transfer.amount_in_cents == 100000
            assert transfer.direction == "INTERNAL"
            assert transfer.origin == "RULE"
            assert transfer.status == "COMPLETE"
            assert transfer.source is not None
            assert transfer.source.name == "Main Payroll"
            assert transfer.destination is not None
            assert transfer.destination.name == "Emergency Fund"
            assert transfer.rule_id == RULE_ID
            assert transfer.rule_execution_id == EXECUTION_ID_1
            assert transfer.completed_at == "2024-04-23T09:15:04Z"
            assert pagination["page"] == 1
            assert pagination["pageSize"] == 10

        @pytest.mark.asyncio
        @respx.mock
        async def it_handles_null_source_for_money_in(
            sample_list_transfers_no_source_response,
        ):
            respx.get(f"{V1_BASE}/accounts/{ACCOUNT_ID}/transfers").mock(
                return_value=httpx.Response(
                    200, json=sample_list_transfers_no_source_response
                )
            )

            async with SequenceClient(access_token="tok") as client:
                items, _ = await client.list_transfers(account_id=ACCOUNT_ID)

            assert len(items) == 1
            assert items[0].source is None
            assert items[0].direction == "MONEY_IN"
            assert items[0].origin == "DIRECT_DEPOSIT"
            assert items[0].rule_id is None
            assert items[0].rule_execution_id is None

        @pytest.mark.asyncio
        @respx.mock
        async def it_passes_page_and_page_size_as_query_params(
            sample_list_transfers_response,
        ):
            route = respx.get(f"{V1_BASE}/accounts/{ACCOUNT_ID}/transfers").mock(
                return_value=httpx.Response(200, json=sample_list_transfers_response)
            )

            async with SequenceClient(access_token="tok") as client:
                await client.list_transfers(
                    account_id=ACCOUNT_ID, page=3, page_size=50
                )

            request = route.calls[0].request
            assert "page=3" in str(request.url)
            assert "pageSize=50" in str(request.url)

        @pytest.mark.asyncio
        @respx.mock
        async def it_raises_on_401(sample_error_response_unauthorized):
            respx.get(f"{V1_BASE}/accounts/{ACCOUNT_ID}/transfers").mock(
                return_value=httpx.Response(
                    401, json=sample_error_response_unauthorized
                )
            )

            async with SequenceClient(access_token="bad") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.list_transfers(account_id=ACCOUNT_ID)

            assert exc_info.value.status_code == 401

        @pytest.mark.asyncio
        @respx.mock
        async def it_raises_on_403(sample_error_response_forbidden):
            respx.get(f"{V1_BASE}/accounts/{ACCOUNT_ID}/transfers").mock(
                return_value=httpx.Response(403, json=sample_error_response_forbidden)
            )

            async with SequenceClient(access_token="tok") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.list_transfers(account_id=ACCOUNT_ID)

            assert exc_info.value.status_code == 403

        @pytest.mark.asyncio
        @respx.mock
        async def it_raises_on_429(sample_error_response_rate_limit):
            respx.get(f"{V1_BASE}/accounts/{ACCOUNT_ID}/transfers").mock(
                return_value=httpx.Response(
                    429, json=sample_error_response_rate_limit
                )
            )

            async with SequenceClient(access_token="tok") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.list_transfers(account_id=ACCOUNT_ID)

            assert exc_info.value.status_code == 429

        @pytest.mark.asyncio
        async def it_raises_value_error_without_token():
            async with SequenceClient() as client:
                with pytest.raises(ValueError):
                    await client.list_transfers(account_id=ACCOUNT_ID)

    # ------------------------------------------------------------------
    # Context manager — v1 client cleanup
    # ------------------------------------------------------------------

    def describe_context_manager_v1():
        """Tests that v1 client is cleaned up on exit."""

        @pytest.mark.asyncio
        async def it_closes_v1_client_on_exit():
            client = SequenceClient(access_token="tok")
            async with client:
                assert client._v1_client is not None
            assert client._v1_client is None

        @pytest.mark.asyncio
        async def it_closes_v1_client_on_close():
            client = SequenceClient(access_token="tok")
            client._get_v1_client()  # force init
            assert client._v1_client is not None
            await client.close()
            assert client._v1_client is None

        @pytest.mark.asyncio
        async def it_handles_exit_when_v1_client_is_none():
            client = SequenceClient(access_token="tok")
            assert client._v1_client is None
            await client.__aexit__(None, None, None)
            assert client._v1_client is None

        @pytest.mark.asyncio
        async def it_handles_close_when_v1_client_is_none():
            client = SequenceClient(access_token="tok")
            assert client._v1_client is None
            await client.close()
            assert client._v1_client is None

    # ------------------------------------------------------------------
    # Error response shape: v1 nested vs legacy flat
    # ------------------------------------------------------------------

    def describe__handle_error_response():
        """Tests that both v1 nested and legacy flat error shapes are handled."""

        @pytest.mark.asyncio
        @respx.mock
        async def it_parses_v1_nested_error_shape():
            """Platform v1 wraps errors as {"requestId": ..., "error": {"code": ..., "message": ...}}."""
            v1_error = {
                "requestId": "req-test-123",
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Unauthorized",
                },
            }
            respx.get(f"{V1_BASE}/rules/{RULE_ID}").mock(
                return_value=httpx.Response(401, json=v1_error)
            )

            async with SequenceClient(access_token="bad") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.get_rule(rule_id=RULE_ID)

            assert exc_info.value.code == "UNAUTHORIZED"
            assert exc_info.value.message == "Unauthorized"
            assert exc_info.value.status_code == 401

        @pytest.mark.asyncio
        @respx.mock
        async def it_parses_legacy_flat_error_shape():
            """Legacy endpoints use flat {"code": ..., "message": ...}."""
            flat_error = {
                "code": "INVALID_ACCESS_TOKEN",
                "message": "Unauthorized",
            }
            respx.post("https://api.getsequence.io/accounts").mock(
                return_value=httpx.Response(401, json=flat_error)
            )

            async with SequenceClient(access_token="bad") as client:
                with pytest.raises(SequenceError) as exc_info:
                    await client.get_accounts()

            assert exc_info.value.code == "INVALID_ACCESS_TOKEN"
            assert exc_info.value.status_code == 401
