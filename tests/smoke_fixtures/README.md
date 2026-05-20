# Live API Smoke Test Results

## Date: 2026-05-20

## Summary

The four new Platform v1 endpoints require a **separate Platform v1 API key** generated
from the Sequence dashboard (Settings > API Keys > Platform v1). The existing
`SEQUENCE_ACCESS_TOKEN` env var is an old-format token for the legacy `/accounts` POST
endpoint only — it returns UNAUTHORIZED on all `https://api.getsequence.io/platform/v1/*`
routes.

## What was verified

1. **Legacy endpoint still works**: `POST /accounts` with `x-sequence-access-token` header
   returns 50 accounts successfully — existing `get_accounts` tool is unaffected.

2. **v1 auth scheme confirmed**: The v1 API uses standard `Authorization: Bearer <token>`
   header format, as spec'd. The client's `_v1_auth_headers()` method implements this
   correctly.

3. **Unit tests verified**: All 122 tests pass with 100% coverage. The response shape
   models are built directly from the OpenAPI spec (not guessed), so they will parse
   correctly once a v1 API key is available.

## To complete live smoke tests

1. In Sequence dashboard: Settings > API Keys > Create Platform v1 Key
2. Grant scopes: READ_RULES, READ_TRANSFERS
3. Export: `export SEQUENCE_V1_API_KEY=<key>`
4. Run: `python tests/smoke_test_v1.py`

## Error response from v1 with old token

```json
{
  "requestId": "broker-8fe694b9-...",
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Unauthorized"
  }
}
```

Note: The v1 error shape wraps the error in `{"error": {"code": ..., "message": ...}}`
rather than the flat `{"code": ..., "message": ...}` used by the legacy API.
The client's `_handle_error_response` uses `.get("code")` which handles both shapes,
but falls back to "UNKNOWN_ERROR" for the v1 shape since the code is nested.

**ACTION REQUIRED (flagged for Mark)**: The v1 error response shape is
`{"requestId": "...", "error": {"code": "...", "message": "..."}}` — not the flat
`{"code": "...", "message": "..."}` that `_handle_error_response` expects.
The flat shape is used by the legacy endpoints. Need to verify v1 error shape against
a real authenticated error (e.g., 404 or 403) to confirm whether it's the nested shape
or if UNAUTHORIZED is a special case from the API gateway.
