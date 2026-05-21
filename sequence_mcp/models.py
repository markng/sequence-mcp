"""Pydantic models for Sequence API responses."""

from typing import Any, Literal
from pydantic import BaseModel, Field


class AccountBalance(BaseModel):
    """Balance information for an account."""

    amount_in_dollars: float | None = Field(
        alias="amountInDollars",
        description="Current available balance in dollars, or None if error occurred",
    )
    error: str | None = Field(
        default=None,
        description="Error message if balance retrieval failed",
    )


class Account(BaseModel):
    """A financial account in Sequence."""

    id: str = Field(description="Unique identifier for the account")
    name: str = Field(description="Display name of the account")
    balance: AccountBalance = Field(description="Balance information")
    type: Literal["Pod", "Income Source", "Account"] = Field(
        description="Type of account"
    )


class AccountsResponseData(BaseModel):
    """Data payload for accounts response."""

    accounts: list[Account] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class AccountsResponse(BaseModel):
    """Response from the accounts endpoint."""

    message: str
    request_id: str = Field(alias="requestId")
    data: AccountsResponseData


class TriggerRuleResponseData(BaseModel):
    """Data payload for trigger rule response."""

    request_id: str = Field(alias="requestId")


class TriggerRuleResponse(BaseModel):
    """Response from triggering a rule."""

    code: str
    message: str
    data: TriggerRuleResponseData


class SequenceErrorResponse(BaseModel):
    """Error response from the API."""

    code: str
    message: str


class SequenceError(Exception):
    """Exception raised for Sequence API errors."""

    def __init__(self, code: str, message: str, status_code: int | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"{code}: {message}")


# ---------------------------------------------------------------------------
# Platform v1 models — Rules
# ---------------------------------------------------------------------------


class RuleTrigger(BaseModel):
    """Trigger configuration for a rule."""

    type: str = Field(description="Trigger type (e.g. ON_FUNDS_TRANSFERRED, SCHEDULED)")
    account_id: str | None = Field(
        default=None,
        alias="accountId",
        description="Account ID for fund-transfer triggers",
    )

    model_config = {"populate_by_name": True, "extra": "allow"}


class RuleActionAccountRef(BaseModel):
    """Account reference within a rule action."""

    id: str
    type: str
    name: str | None = None

    model_config = {"extra": "allow"}


class RuleAction(BaseModel):
    """A single action within a rule step."""

    type: str = Field(description="Action type (e.g. FIXED, PERCENTAGE)")
    amount_in_cents: int | None = Field(default=None, alias="amountInCents")
    percentage_value: float | None = Field(default=None, alias="percentageValue")
    percentage_target: str | None = Field(default=None, alias="percentageTarget")
    source: RuleActionAccountRef | None = None
    destination: RuleActionAccountRef | None = None
    group_index: int | None = Field(default=None, alias="groupIndex")
    up_to_enabled: bool | None = Field(default=None, alias="upToEnabled")
    is_direct_deposit: bool | None = Field(default=None, alias="isDirectDeposit")
    limit: Any = None
    ach_description: str | None = Field(default=None, alias="achDescription")

    model_config = {"populate_by_name": True, "extra": "allow"}


class RuleConditionExpr(BaseModel):
    """A single condition expression."""

    fact: str | None = None
    operator: str | None = None
    value: Any = None
    value_fact: Any = Field(default=None, alias="valueFact")
    params: Any = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class RuleConditions(BaseModel):
    """Conditions block for a rule step."""

    condition: RuleConditionExpr | None = None

    model_config = {"extra": "allow"}


class RuleStep(BaseModel):
    """A single step in a rule."""

    conditions: RuleConditions | None = None
    actions: list[RuleAction] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class Rule(BaseModel):
    """A Sequence automation rule."""

    id: str
    name: str | None = None
    description: str | None = None
    status: Literal["ENABLED", "DISABLED"]
    trigger: RuleTrigger
    steps: list[RuleStep]
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    deleted_at: str | None = Field(default=None, alias="deletedAt")

    model_config = {"populate_by_name": True, "extra": "allow"}

    def to_tool_payload(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict suitable for MCP tool responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "trigger": self.trigger.model_dump(by_alias=False, exclude_none=True),
            "steps": [
                {
                    "conditions": step.conditions.model_dump(
                        by_alias=False, exclude_none=True
                    )
                    if step.conditions
                    else None,
                    "actions": [
                        action.model_dump(by_alias=False, exclude_none=True)
                        for action in step.actions
                    ],
                }
                for step in self.steps
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deleted_at": self.deleted_at,
        }


class GetRuleResponse(BaseModel):
    """Response from GET /rules/{id}."""

    request_id: str = Field(alias="requestId")
    data: Rule

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Platform v1 models — Rule Executions
# ---------------------------------------------------------------------------


class RuleExecutionSummary(BaseModel):
    """Lightweight rule execution as returned by the list endpoint."""

    id: str
    rule_id: str = Field(alias="ruleId")
    status: Literal["EXECUTED", "PARTIAL", "IN_PROGRESS", "FAILED"]
    created_at: str = Field(alias="createdAt")

    model_config = {"populate_by_name": True, "extra": "allow"}

    def to_tool_payload(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict suitable for MCP tool responses."""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "status": self.status,
            "created_at": self.created_at,
        }


class TriggerDetails(BaseModel):
    """Details about what triggered a rule execution."""

    type: str = Field(
        description="Trigger type (MANUAL, SCHEDULED, ON_FUNDS_TRANSFERRED)"
    )
    amount_in_cents: int | None = Field(default=None, alias="amountInCents")
    scheduled_time: str | None = Field(default=None, alias="scheduledTime")

    model_config = {"populate_by_name": True, "extra": "allow"}


class RuleExecution(RuleExecutionSummary):
    """Full rule execution including trigger details and transfer outcome."""

    trigger_details: TriggerDetails = Field(alias="triggerDetails")
    step_index_matched: int | None = Field(alias="stepIndexMatched")
    conditions_not_met: bool = Field(alias="conditionsNotMet")
    transfers_attempted: int = Field(alias="transfersAttempted")
    transfers_completed: int = Field(alias="transfersCompleted")
    transfers_failed: int = Field(alias="transfersFailed")
    transfers_pending: int = Field(alias="transfersPending")
    transfer_ids: list[str] = Field(alias="transferIds")
    error_message: str | None = Field(alias="errorMessage")
    next_attempt_at: str | None = Field(alias="nextAttemptAt")

    model_config = {"populate_by_name": True, "extra": "allow"}

    def to_tool_payload(self) -> dict[str, Any]:  # type: ignore[override]
        """Return a JSON-serialisable dict suitable for MCP tool responses."""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "status": self.status,
            "created_at": self.created_at,
            "trigger_details": self.trigger_details.model_dump(
                by_alias=False, exclude_none=True
            ),
            "step_index_matched": self.step_index_matched,
            "conditions_not_met": self.conditions_not_met,
            "transfers_attempted": self.transfers_attempted,
            "transfers_completed": self.transfers_completed,
            "transfers_failed": self.transfers_failed,
            "transfers_pending": self.transfers_pending,
            "transfer_ids": self.transfer_ids,
            "error_message": self.error_message,
            "next_attempt_at": self.next_attempt_at,
        }


class Pagination(BaseModel):
    """Pagination metadata."""

    page: int
    page_size: int = Field(alias="pageSize")

    model_config = {"populate_by_name": True}


class PaginatedRuleExecutionsData(BaseModel):
    """Paginated list of rule execution summaries."""

    items: list[RuleExecutionSummary]
    pagination: Pagination


class ListRuleExecutionsResponse(BaseModel):
    """Response from GET /rules/{ruleId}/executions."""

    request_id: str = Field(alias="requestId")
    data: PaginatedRuleExecutionsData

    model_config = {"populate_by_name": True}


class GetRuleExecutionResponse(BaseModel):
    """Response from GET /rules/{ruleId}/executions/{id}."""

    request_id: str = Field(alias="requestId")
    data: RuleExecution

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Platform v1 models — Transfers
# ---------------------------------------------------------------------------


class TransferAccountRef(BaseModel):
    """Account reference within a transfer."""

    id: str
    name: str | None = None
    type: str
    is_deleted: bool = Field(alias="isDeleted")

    model_config = {"populate_by_name": True, "extra": "allow"}


class Transfer(BaseModel):
    """A single money movement."""

    id: str
    amount_in_cents: int = Field(alias="amountInCents")
    direction: Literal["MONEY_IN", "MONEY_OUT", "INTERNAL"]
    origin: str
    status: Literal[
        "PENDING_APPROVAL",
        "PROCESSING",
        "PENDING",
        "COMPLETE",
        "INCOMPLETE",
        "ERROR",
        "CANCELLED",
    ]
    source: TransferAccountRef | None = None
    destination: TransferAccountRef | None = None
    rule_id: str | None = Field(default=None, alias="ruleId")
    rule_execution_id: str | None = Field(default=None, alias="ruleExecutionId")
    error_code: str | None = Field(default=None, alias="errorCode")
    created_at: str = Field(alias="createdAt")
    completed_at: str | None = Field(default=None, alias="completedAt")

    model_config = {"populate_by_name": True, "extra": "allow"}

    def to_tool_payload(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict suitable for MCP tool responses."""
        return {
            "id": self.id,
            "amount_in_cents": self.amount_in_cents,
            "amount_in_dollars": self.amount_in_cents / 100,
            "direction": self.direction,
            "origin": self.origin,
            "status": self.status,
            "source": self.source.model_dump(by_alias=False) if self.source else None,
            "destination": (
                self.destination.model_dump(by_alias=False)
                if self.destination
                else None
            ),
            "rule_id": self.rule_id,
            "rule_execution_id": self.rule_execution_id,
            "error_code": self.error_code,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class PaginatedTransfersData(BaseModel):
    """Paginated list of transfers."""

    items: list[Transfer]
    pagination: Pagination


class ListTransfersResponse(BaseModel):
    """Response from GET /accounts/{accountId}/transfers."""

    request_id: str = Field(alias="requestId")
    data: PaginatedTransfersData

    model_config = {"populate_by_name": True}
