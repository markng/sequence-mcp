"""Shared test fixtures."""

import pytest


@pytest.fixture
def sample_accounts_response():
    """Sample response from the accounts endpoint."""
    return {
        "message": "OK",
        "requestId": "f1a2b3c4-56d7-890e-fgh1-XXXXXXXXXXXX",
        "data": {
            "accounts": [
                {
                    "id": "5579244",
                    "name": "Main Operating Pod",
                    "balance": {"amountInDollars": 25342.77, "error": None},
                    "type": "Pod",
                },
                {
                    "id": "5579245",
                    "name": "Client Payments Account",
                    "balance": {"amountInDollars": 10200.50, "error": None},
                    "type": "Income Source",
                },
                {
                    "id": "QDBZQjj1lohgeqVWJlnmf5lA4g83ZGCwl3Qx4",
                    "name": "Chase Credit Card",
                    "balance": {"amountInDollars": 137.9, "error": None},
                    "type": "Account",
                },
            ],
            "errors": [],
        },
    }


@pytest.fixture
def sample_trigger_response():
    """Sample response from the trigger rule endpoint."""
    return {
        "code": "OK",
        "message": "Rule with id ru_12345 has been triggered",
        "data": {"requestId": "b28f1d9e-8c2a-4d3e-9af1-XXXXXXXXXXXX"},
    }


@pytest.fixture
def sample_error_response_unauthorized():
    """Sample unauthorized error response."""
    return {"code": "INVALID_ACCESS_TOKEN", "message": "Unauthorized"}


@pytest.fixture
def sample_error_response_invalid_secret():
    """Sample invalid API secret error response."""
    return {"code": "INVALID_API_SECRET", "message": "Unauthorized"}


@pytest.fixture
def sample_error_response_rate_limit():
    """Sample rate limit error response."""
    return {
        "code": "TOO_MANY_REQUESTS",
        "message": "Rule with id ru_12345 has been triggered too many times. Please try again later.",
    }


@pytest.fixture
def sample_error_response_not_found():
    """Sample 404 not found error response."""
    return {"code": "NOT_FOUND", "message": "Resource not found"}


@pytest.fixture
def sample_error_response_forbidden():
    """Sample 403 forbidden error response."""
    return {"code": "FORBIDDEN", "message": "Insufficient permissions"}


# ---------------------------------------------------------------------------
# Platform v1 error fixtures — nested shape
# {"requestId": ..., "error": {"code": ..., "message": ...}}
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_v1_error_unauthorized():
    """Platform v1 401 unauthorized response (nested shape)."""
    return {
        "requestId": "req-err-401",
        "error": {"code": "UNAUTHORIZED", "message": "Invalid or expired API key"},
    }


@pytest.fixture
def sample_v1_error_not_found():
    """Platform v1 404 not found response (nested shape)."""
    return {
        "requestId": "req-err-404",
        "error": {"code": "NOT_FOUND", "message": "Resource not found"},
    }


@pytest.fixture
def sample_v1_error_forbidden():
    """Platform v1 403 forbidden response (nested shape)."""
    return {
        "requestId": "req-err-403",
        "error": {
            "code": "FORBIDDEN",
            "message": "API key lacks required scope",
        },
    }


@pytest.fixture
def sample_v1_error_rate_limit():
    """Platform v1 429 rate limit response (nested shape)."""
    return {
        "requestId": "req-err-429",
        "error": {
            "code": "TOO_MANY_REQUESTS",
            "message": "Rate limit exceeded, please retry after 60 seconds",
        },
    }


# ---------------------------------------------------------------------------
# Platform v1 fixtures — Rules
# ---------------------------------------------------------------------------

RULE_ID = "551ff9b6-ddf1-4110-b611-1b11044b72d4"
EXECUTION_ID_1 = "4306b3e8-6e77-4c08-ab0b-bb33654af44c"
EXECUTION_ID_2 = "4fde08bb-8f17-45ec-9d3f-a30c6ffc1351"
ACCOUNT_ID = "c7a7f26f-2ca5-4ae5-825a-70260591247c"


@pytest.fixture
def sample_rule_response():
    """Sample response from GET /rules/{id}."""
    return {
        "requestId": "req-5006",
        "data": {
            "id": RULE_ID,
            "name": "Auto-save on deposit",
            "description": "Saves 20% of every incoming deposit",
            "status": "ENABLED",
            "trigger": {
                "type": "ON_FUNDS_TRANSFERRED",
                "accountId": ACCOUNT_ID,
            },
            "steps": [
                {
                    "conditions": {
                        "condition": {
                            "fact": "BALANCE",
                            "operator": "GREATER_THAN",
                            "value": 50000,
                            "valueFact": None,
                            "params": None,
                        }
                    },
                    "actions": [
                        {
                            "type": "PERCENTAGE",
                            "percentageValue": 20.0,
                            "percentageTarget": "INCOMING_AMOUNT",
                            "source": {
                                "id": ACCOUNT_ID,
                                "type": "INCOME_SOURCE",
                                "name": None,
                            },
                            "destination": {
                                "id": "57ee255e-b1d7-4da4-8080-edbf783b0898",
                                "type": "POD",
                                "name": None,
                            },
                            "groupIndex": 0,
                            "upToEnabled": False,
                            "isDirectDeposit": False,
                            "limit": None,
                            "achDescription": None,
                        }
                    ],
                }
            ],
            "createdAt": "2024-03-01T10:00:00Z",
            "updatedAt": "2024-03-15T14:30:00Z",
            "deletedAt": None,
        },
    }


@pytest.fixture
def sample_list_rule_executions_response():
    """Sample response from GET /rules/{ruleId}/executions."""
    return {
        "requestId": "req-5007",
        "data": {
            "items": [
                {
                    "id": EXECUTION_ID_1,
                    "ruleId": RULE_ID,
                    "status": "EXECUTED",
                    "createdAt": "2024-04-23T09:15:00Z",
                },
                {
                    "id": EXECUTION_ID_2,
                    "ruleId": RULE_ID,
                    "status": "PARTIAL",
                    "createdAt": "2024-04-20T08:00:00Z",
                },
            ],
            "pagination": {"page": 1, "pageSize": 10},
        },
    }


@pytest.fixture
def sample_get_rule_execution_response():
    """Sample response from GET /rules/{ruleId}/executions/{id} (successful execution)."""
    return {
        "requestId": "req-5008",
        "data": {
            "id": EXECUTION_ID_1,
            "ruleId": RULE_ID,
            "status": "EXECUTED",
            "createdAt": "2024-04-23T09:15:00Z",
            "triggerDetails": {
                "type": "ON_FUNDS_TRANSFERRED",
                "amountInCents": 250000,
            },
            "stepIndexMatched": 0,
            "conditionsNotMet": False,
            "transfersAttempted": 2,
            "transfersCompleted": 2,
            "transfersFailed": 0,
            "transfersPending": 0,
            "transferIds": [
                "809e5e0b-bb0b-49b2-867a-8b44d04d9179",
                "32a4182a-38b5-4058-98da-4d1b3d13ab72",
            ],
            "errorMessage": None,
            "nextAttemptAt": None,
        },
    }


@pytest.fixture
def sample_get_rule_execution_failed_response():
    """Sample response from GET /rules/{ruleId}/executions/{id} (failed execution)."""
    return {
        "requestId": "req-5010",
        "data": {
            "id": "0d6195f3-c855-4cc0-b150-3364bf57d07d",
            "ruleId": RULE_ID,
            "status": "FAILED",
            "createdAt": "2024-04-18T14:30:00Z",
            "triggerDetails": {
                "type": "MANUAL",
                "amountInCents": 150000,
            },
            "stepIndexMatched": 0,
            "conditionsNotMet": False,
            "transfersAttempted": 1,
            "transfersCompleted": 0,
            "transfersFailed": 1,
            "transfersPending": 0,
            "transferIds": ["b6fa092e-834a-4e08-a7fc-20f7e5260dd5"],
            "errorMessage": "Insufficient funds in source account.",
            "nextAttemptAt": None,
        },
    }


# ---------------------------------------------------------------------------
# Platform v1 fixtures — Transfers
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_list_transfers_response():
    """Sample response from GET /accounts/{accountId}/transfers."""
    return {
        "requestId": "req-5002",
        "data": {
            "items": [
                {
                    "id": "809e5e0b-bb0b-49b2-867a-8b44d04d9179",
                    "amountInCents": 100000,
                    "direction": "INTERNAL",
                    "origin": "RULE",
                    "status": "COMPLETE",
                    "source": {
                        "id": ACCOUNT_ID,
                        "name": "Main Payroll",
                        "type": "INCOME_SOURCE",
                        "isDeleted": False,
                    },
                    "destination": {
                        "id": "c2cb3499-2491-4185-a6f5-1a3d281b875a",
                        "name": "Emergency Fund",
                        "type": "POD",
                        "isDeleted": False,
                    },
                    "ruleId": RULE_ID,
                    "ruleExecutionId": EXECUTION_ID_1,
                    "errorCode": None,
                    "createdAt": "2024-04-23T09:15:00Z",
                    "completedAt": "2024-04-23T09:15:04Z",
                }
            ],
            "pagination": {"page": 1, "pageSize": 10},
        },
    }


@pytest.fixture
def sample_list_transfers_no_source_response():
    """Sample transfers response with null source (MONEY_IN direct deposit)."""
    return {
        "requestId": "req-5003",
        "data": {
            "items": [
                {
                    "id": "aabb1122-0000-0000-0000-000000000001",
                    "amountInCents": 500000,
                    "direction": "MONEY_IN",
                    "origin": "DIRECT_DEPOSIT",
                    "status": "COMPLETE",
                    "source": None,
                    "destination": {
                        "id": ACCOUNT_ID,
                        "name": "Main Payroll",
                        "type": "INCOME_SOURCE",
                        "isDeleted": False,
                    },
                    "ruleId": None,
                    "ruleExecutionId": None,
                    "errorCode": None,
                    "createdAt": "2024-04-24T12:00:00Z",
                    "completedAt": "2024-04-24T12:00:05Z",
                }
            ],
            "pagination": {"page": 1, "pageSize": 10},
        },
    }
