"""Async client for the Sequence Banking API."""

from typing import Any
import httpx

from .models import (
    Account,
    AccountsResponse,
    GetRuleResponse,
    GetRuleExecutionResponse,
    ListRuleExecutionsResponse,
    ListTransfersResponse,
    Rule,
    RuleExecution,
    RuleExecutionSummary,
    Transfer,
    TriggerRuleResponse,
    SequenceError,
)

# Base URL for the Platform v1 API
PLATFORM_V1_BASE_URL = "https://api.getsequence.io/platform/v1"


class SequenceClient:
    """Async client for interacting with the Sequence Banking API.

    The client supports two authentication methods:
    - Access token (Bearer): For all Platform v1 operations and account fetching.
    - API secret: For legacy per-rule webhook triggers (trigger_rule).
    """

    BASE_URL = "https://api.getsequence.io"
    PLATFORM_V1_BASE_URL = PLATFORM_V1_BASE_URL

    def __init__(
        self,
        access_token: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the Sequence client.

        Args:
            access_token: User access token for account operations and Platform v1.
            timeout: Request timeout in seconds.
        """
        self.access_token = access_token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._v1_client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "SequenceClient":
        """Enter async context manager."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.timeout,
        )
        self._v1_client = httpx.AsyncClient(
            base_url=self.PLATFORM_V1_BASE_URL,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._v1_client:
            await self._v1_client.aclose()
            self._v1_client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get the legacy HTTP client, creating one if necessary."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=self.timeout,
            )
        return self._client

    def _get_v1_client(self) -> httpx.AsyncClient:
        """Get the Platform v1 HTTP client, creating one if necessary."""
        if self._v1_client is None:
            self._v1_client = httpx.AsyncClient(
                base_url=self.PLATFORM_V1_BASE_URL,
                timeout=self.timeout,
            )
        return self._v1_client

    async def close(self) -> None:
        """Close the HTTP clients."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._v1_client:
            await self._v1_client.aclose()
            self._v1_client = None

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the API.

        Supports two error response shapes:
        - Legacy (flat):  {"code": "...", "message": "..."}
        - Platform v1 (nested): {"requestId": "...", "error": {"code": "...", "message": "..."}}
        """
        try:
            data = response.json()
            # Platform v1 nests the error under an "error" key
            error_obj = data.get("error") or data
            code = error_obj.get("code", "UNKNOWN_ERROR")
            message = error_obj.get("message", "Unknown error")
        except Exception:
            code = "HTTP_ERROR"
            message = f"HTTP {response.status_code}: {response.text}"

        raise SequenceError(code=code, message=message, status_code=response.status_code)

    def _v1_auth_headers(self) -> dict[str, str]:
        """Return Authorization header for Platform v1 requests."""
        if not self.access_token:
            raise ValueError("Access token is required for Platform v1 operations")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "x-called-reason": "MCP tool call from sequence-mcp agent",
        }

    # ------------------------------------------------------------------
    # Legacy endpoints
    # ------------------------------------------------------------------

    async def get_accounts(self) -> list[Account]:
        """Fetch all accounts with their balances.

        Returns:
            List of Account objects with balance information.

        Raises:
            SequenceError: If the API request fails.
            ValueError: If no access token is configured.
        """
        if not self.access_token:
            raise ValueError("Access token is required for fetching accounts")

        client = self._get_client()
        response = await client.post(
            "/accounts",
            headers={
                "x-sequence-access-token": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json={},
        )

        if response.status_code != 200:
            self._handle_error_response(response)

        accounts_response = AccountsResponse.model_validate(response.json())
        return accounts_response.data.accounts

    async def trigger_rule(
        self,
        rule_id: str,
        api_secret: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> TriggerRuleResponse:
        """Trigger a rule via the legacy per-rule webhook API.

        Args:
            rule_id: The ID of the rule to trigger (e.g., "ru_12345").
            api_secret: The API secret associated with the rule.
            payload: Optional JSON payload to send with the trigger.
            idempotency_key: Optional key to prevent duplicate triggers.

        Returns:
            TriggerRuleResponse with the result of the trigger.

        Raises:
            SequenceError: If the API request fails.
        """
        client = self._get_client()

        headers = {
            "x-sequence-signature": f"Bearer {api_secret}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["idempotency-key"] = idempotency_key

        response = await client.post(
            f"/remote-api/rules/{rule_id}/trigger",
            headers=headers,
            json=payload or {},
        )

        if response.status_code != 200:
            self._handle_error_response(response)

        return TriggerRuleResponse.model_validate(response.json())

    # ------------------------------------------------------------------
    # Platform v1 endpoints — Rules
    # ------------------------------------------------------------------

    async def get_rule(self, rule_id: str) -> Rule:
        """Get a rule by ID including all steps, conditions, and actions.

        Args:
            rule_id: UUID of the rule.

        Returns:
            Rule object with full composition.

        Raises:
            SequenceError: If the API request fails (401, 403, 404, 429).
            ValueError: If no access token is configured.
        """
        client = self._get_v1_client()
        response = await client.get(
            f"/rules/{rule_id}",
            headers=self._v1_auth_headers(),
        )

        if response.status_code != 200:
            self._handle_error_response(response)

        parsed = GetRuleResponse.model_validate(response.json())
        return parsed.data

    async def list_rule_executions(
        self,
        rule_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[RuleExecutionSummary], dict[str, int]]:
        """List executions for a rule, ordered newest first.

        Args:
            rule_id: UUID of the rule.
            page: 1-based page index (default 1).
            page_size: Items per page, max 100 (default 10).

        Returns:
            Tuple of (items, pagination) where pagination is
            {"page": int, "pageSize": int}.

        Raises:
            SequenceError: If the API request fails.
            ValueError: If no access token is configured.
        """
        client = self._get_v1_client()
        response = await client.get(
            f"/rules/{rule_id}/executions",
            params={"page": page, "pageSize": page_size},
            headers=self._v1_auth_headers(),
        )

        if response.status_code != 200:
            self._handle_error_response(response)

        parsed = ListRuleExecutionsResponse.model_validate(response.json())
        pagination = {
            "page": parsed.data.pagination.page,
            "pageSize": parsed.data.pagination.page_size,
        }
        return parsed.data.items, pagination

    async def get_rule_execution(
        self, rule_id: str, execution_id: str
    ) -> RuleExecution:
        """Get a single rule execution with full detail.

        Args:
            rule_id: UUID of the rule.
            execution_id: UUID of the specific execution.

        Returns:
            RuleExecution with trigger details and transfer outcome.

        Raises:
            SequenceError: If the API request fails (401, 403, 404, 429).
            ValueError: If no access token is configured.
        """
        client = self._get_v1_client()
        response = await client.get(
            f"/rules/{rule_id}/executions/{execution_id}",
            headers=self._v1_auth_headers(),
        )

        if response.status_code != 200:
            self._handle_error_response(response)

        parsed = GetRuleExecutionResponse.model_validate(response.json())
        return parsed.data

    # ------------------------------------------------------------------
    # Platform v1 endpoints — Transfers
    # ------------------------------------------------------------------

    async def list_transfers(
        self,
        account_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Transfer], dict[str, int]]:
        """List transfers for an account, ordered newest first.

        Note: credit card and debit card transactions are excluded by the API.

        Args:
            account_id: UUID of the account.
            page: 1-based page index (default 1).
            page_size: Items per page, max 100 (default 10).

        Returns:
            Tuple of (items, pagination) where pagination is
            {"page": int, "pageSize": int}.

        Raises:
            SequenceError: If the API request fails.
            ValueError: If no access token is configured.
        """
        client = self._get_v1_client()
        response = await client.get(
            f"/accounts/{account_id}/transfers",
            params={"page": page, "pageSize": page_size},
            headers=self._v1_auth_headers(),
        )

        if response.status_code != 200:
            self._handle_error_response(response)

        parsed = ListTransfersResponse.model_validate(response.json())
        pagination = {
            "page": parsed.data.pagination.page,
            "pageSize": parsed.data.pagination.page_size,
        }
        return parsed.data.items, pagination
