"""Smoke test for the four Tier 1 Platform v1 endpoints.

Run as: python tests/smoke_v1.py

Requires:
    SEQUENCE_V1_API_KEY — Platform v1 API key with READ_RULES + READ_TRANSFERS

The test prints the status and first-record snippet for each endpoint and exits
non-zero if any endpoint fails.  No real Sequence response is committed here;
output goes to stdout only.

This file is named smoke_v1.py (not test_smoke_v1.py) so pytest does NOT
auto-collect it.  Run it manually once you have a v1 key.
"""

import asyncio
import os
import sys

# Allow running from either the repo root or the tests/ directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sequence_mcp.client import SequenceClient  # noqa: E402


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"ERROR: {name} is not set.", file=sys.stderr)
        print(
            "Generate a Platform v1 API key from the Sequence dashboard "
            "(Settings > API Keys) with READ_RULES and READ_TRANSFERS scopes, "
            f"then export {name}=<key>.",
            file=sys.stderr,
        )
        sys.exit(1)
    return value


async def _run_smoke(v1_key: str, rule_id: str, account_id: str) -> bool:
    """Hit all four v1 endpoints; return True if all succeed."""
    failures: list[str] = []

    async with SequenceClient(access_token=v1_key) as client:
        # 1. get_rule
        print(f"\n[1/4] get_rule({rule_id!r})")
        try:
            rule = await client.get_rule(rule_id=rule_id)
            print(f"  OK  id={rule.id} name={rule.name!r} status={rule.status}")
        except Exception as exc:
            print(f"  FAIL  {exc}")
            failures.append("get_rule")

        # 2. list_rule_executions
        print(f"\n[2/4] list_rule_executions({rule_id!r})")
        try:
            items, pagination = await client.list_rule_executions(rule_id=rule_id)
            first = items[0] if items else None
            print(
                f"  OK  count={len(items)} page={pagination} "
                + (
                    f"first_id={first.id!r} status={first.status}"
                    if first
                    else "(empty)"
                )
            )
            exec_id = first.id if first else None
        except Exception as exc:
            print(f"  FAIL  {exc}")
            failures.append("list_rule_executions")
            exec_id = None

        # 3. get_rule_execution (skipped if list returned nothing)
        if exec_id:
            print(f"\n[3/4] get_rule_execution({rule_id!r}, {exec_id!r})")
            try:
                execution = await client.get_rule_execution(
                    rule_id=rule_id, execution_id=exec_id
                )
                print(
                    f"  OK  status={execution.status} "
                    f"completed={execution.transfers_completed} "
                    f"failed={execution.transfers_failed}"
                )
            except Exception as exc:
                print(f"  FAIL  {exc}")
                failures.append("get_rule_execution")
        else:
            print("\n[3/4] get_rule_execution  SKIPPED (no executions found)")

        # 4. list_transfers
        print(f"\n[4/4] list_transfers({account_id!r})")
        try:
            transfers, pagination = await client.list_transfers(account_id=account_id)
            first_t = transfers[0] if transfers else None
            print(
                f"  OK  count={len(transfers)} page={pagination} "
                + (
                    f"first_id={first_t.id!r} dir={first_t.direction} "
                    f"status={first_t.status}"
                    if first_t
                    else "(empty)"
                )
            )
        except Exception as exc:
            print(f"  FAIL  {exc}")
            failures.append("list_transfers")

    return not failures


def main() -> None:
    v1_key = _require_env("SEQUENCE_V1_API_KEY")

    rule_id = os.environ.get("SMOKE_RULE_ID", "")
    account_id = os.environ.get("SMOKE_ACCOUNT_ID", "")

    if not rule_id or not account_id:
        print(
            "ERROR: set SMOKE_RULE_ID and SMOKE_ACCOUNT_ID to UUIDs from your Sequence account.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("=== Sequence MCP Platform v1 smoke test ===")
    print(f"  v1 key length : {len(v1_key)} chars")
    print(f"  rule_id       : {rule_id}")
    print(f"  account_id    : {account_id}")

    ok = asyncio.run(_run_smoke(v1_key, rule_id, account_id))

    print()
    if ok:
        print("All endpoints OK.")
        sys.exit(0)
    else:
        print("One or more endpoints FAILED — see output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
