from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "review_items.json"

ReviewAction = Literal["claim", "approve", "reject", "escalate"]

CURRENT_REVIEWER = "alex"
TERMINAL_STATUSES = {"approved", "rejected", "escalated"}
RISK_RANK = {"high": 0, "medium": 1, "low": 2}
TIER_RANK = {"priority": 0, "standard": 1}


class ActionRequest(BaseModel):
    action: ReviewAction


app = FastAPI(title="Reviewer Queue API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_seed_items() -> list[dict]:
    with DATA_FILE.open() as file:
        return json.load(file)


ITEMS = load_seed_items()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/dev/reset")
async def reset_items() -> dict:
    global ITEMS
    ITEMS = load_seed_items()
    return {"items": deepcopy(ITEMS)}


@app.get("/review-items")
async def list_review_items(active_only: bool = True) -> dict:
    items = deepcopy(ITEMS)

    if active_only:
        items = [item for item in items if item["status"] not in TERMINAL_STATUSES]

    items.sort(key=queue_order_key)
    return {"items": items}


def queue_order_key(item: dict) -> tuple:
    return (
        RISK_RANK.get(item["risk_level"], 99),
        TIER_RANK.get(item["customer_tier"], 99),
        item["submitted_at"],
    )


@app.get("/review-items/{item_id}")
async def get_review_item(item_id: str) -> dict:
    item = find_item(item_id)
    return {"item": deepcopy(item)}


@app.post("/review-items/{item_id}/actions")
async def apply_action(item_id: str, request: ActionRequest) -> dict:
    item = find_item(item_id)

    if request.action == "claim":
        if item["status"] != "unassigned":
            raise HTTPException(status_code=409, detail="Only unassigned items can be claimed")
        item["status"] = "in_review"
        item["assigned_reviewer"] = CURRENT_REVIEWER
    else:
        if item["status"] != "in_review":
            raise HTTPException(
                status_code=409,
                detail=f"Only items being reviewed can be {request.action}d",
            )
        item["status"] = status_for_action(request.action)

    return {"item": deepcopy(item)}


def find_item(item_id: str) -> dict:
    for item in ITEMS:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Review item not found")


def status_for_action(action: ReviewAction) -> str:
    if action == "approve":
        return "approved"
    if action == "reject":
        return "rejected"
    if action == "escalate":
        return "escalated"
    return "in_review"
