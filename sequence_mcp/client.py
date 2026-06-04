"""Async client for the Sequence Banking API."""

from typing import Any
import httpx

from .models import (
    Account,
    AccountsResponse,
    TriggerRuleResponse,
    SequenceError,
)


class SequenceClient:
    """Async client for interacting with the Sequence Banking API.

    The client supports two authentication methods:
    - Access token: For user-context operations like fetching accounts
    - API secret: For rule triggers (per-rule secrets)
    """

    BASE_URL = "https://api.getsequence.io"

    def __init__(
        self,
        access_token: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the Sequence client.

        Args:
            access_token: User access token for account operations.
            timeout: Request timeout in seconds.
        """
        self.access_token = access_token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "SequenceClient":
        """Enter async context manager."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get the HTTP client, creating one if necessary."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the API."""
        try:
            data = response.json()
            code = data.get("code", "UNKNOWN_ERROR")
            message = data.get("message", "Unknown error")
        except Exception:
            code = "HTTP_ERROR"
            message = f"HTTP {response.status_code}: {response.text}"

        raise SequenceError(
            code=code, message=message, status_code=response.status_code
        )

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
        """Trigger a rule via the API.

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
