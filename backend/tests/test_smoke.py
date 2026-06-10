import asyncio

import pytest
from fastapi import HTTPException

from app.main import (
    ActionRequest,
    apply_action,
    health,
    list_review_items,
    reset_items,
)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def fresh_state() -> None:
    run(reset_items())


def test_health_check() -> None:
    assert run(health()) == {"status": "ok"}


def test_claim_only_allowed_on_unassigned_items() -> None:
    result = run(apply_action("RV-1024", ActionRequest(action="claim")))
    item = result["item"]
    assert item["status"] == "in_review"
    assert item["assigned_reviewer"] == "alex"

    with pytest.raises(HTTPException) as exc_info:
        run(apply_action("RV-1027", ActionRequest(action="claim")))
    assert exc_info.value.status_code == 409


def test_actions_only_allowed_on_in_review_items() -> None:
    with pytest.raises(HTTPException) as exc_info:
        run(apply_action("RV-1024", ActionRequest(action="approve")))
    assert exc_info.value.status_code == 409

    result = run(apply_action("RV-1027", ActionRequest(action="approve")))
    assert result["item"]["status"] == "approved"

    with pytest.raises(HTTPException) as exc_info:
        run(apply_action("RV-1027", ActionRequest(action="reject")))
    assert exc_info.value.status_code == 409


def test_active_queue_excludes_terminals_and_orders_by_urgency() -> None:
    result = run(list_review_items(active_only=True))
    items = result["items"]

    assert all(item["status"] not in {"approved", "rejected", "escalated"} for item in items)

    first = items[0]
    assert first["risk_level"] == "high"
    assert first["customer_tier"] == "priority"

    high_priority = [it for it in items if it["risk_level"] == "high" and it["customer_tier"] == "priority"]
    assert high_priority[0]["submitted_at"] < high_priority[1]["submitted_at"]
