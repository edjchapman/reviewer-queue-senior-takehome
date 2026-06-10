# Submission

## Summary of changes

Enforced the brief's four workflow rules end-to-end (backend, tests, UI), reordered the active queue by urgency (risk → customer tier → time-asc), and gated the reviewer's action buttons by the current item's state so invalid actions are never offered. Three behaviour-pinning tests cover the rules.

## Bugs fixed

1. **Claim was allowed on already-in-review items.** `apply_action` only blocked terminal statuses, so a `claim` against an `in_review` item silently overwrote `assigned_reviewer`. Now requires `status == "unassigned"`; 409 otherwise. (`backend/app/main.py`)
2. **Approve / reject / escalate were allowed on any non-approved item.** The same handler accepted these against `unassigned` items, skipping the claim step. Now requires `status == "in_review"`; 409 otherwise. (`backend/app/main.py`)
3. **Active queue ordering ignored urgency.** Items were sorted by `submitted_at` descending only. Now sorts by `risk_level` (high > medium > low) → `customer_tier` (priority > standard) → `submitted_at` ascending, via a `queue_order_key` tuple. (`backend/app/main.py`)
4. **`active_only` filter only excluded `approved`.** `rejected` and `escalated` still appeared. Now filters all three terminal statuses. (`backend/app/main.py`)
5. **Reviewer identity was client-controlled.** Backend accepted any string in the request body, undermining "who owns this item right now?". Now uses a server-side `CURRENT_REVIEWER = "alex"` constant; the frontend can still send the field but the backend ignores it.

## Product/UX decisions

- **State-aware action affordances (the deliberate UX improvement).** The four hard-coded action buttons are replaced with a `v-for` over a `validActions` computed that mirrors the backend state machine: `unassigned` → only Claim, `in_review` → Approve/Reject/Escalate, terminal → no buttons + a "no further actions allowed" note. The brief asks "what actions are allowed on this item right now?" — the UI should answer that visibly, not by issuing a 409 after the click.
- **Empty-state for the active queue.** When all items are terminal the workspace shows "The active queue is clear" instead of a blank panel.
- **Refetch after each action.** Cleaner than mutating the local items array in place — terminal items correctly leave the active queue and the next-most-urgent item is selected automatically.
- **Backend error detail surfaced in toasts.** The 409 message ("Only unassigned items can be claimed") now appears in the UI instead of the previous generic "That action could not be completed."
- **Server-side reviewer.** See bug 5 above — a UX decision as much as a correctness one, because it makes ownership reliable.

## Tests added

`backend/tests/test_smoke.py` is replaced. The new file has an autouse `fresh_state` fixture that calls `reset_items()` between tests, then three behaviour tests:

- `test_claim_only_allowed_on_unassigned_items` — claim succeeds on `RV-1024` (unassigned), fails 409 on `RV-1027` (in_review).
- `test_actions_only_allowed_on_in_review_items` — approve fails 409 on unassigned, succeeds on in_review, fails 409 on the now-terminal item.
- `test_active_queue_excludes_terminals_and_orders_by_urgency` — verifies no terminal items in the active queue, that the first item is high-risk + priority, and that older outranks newer within the high-priority bucket.

Run: `cd backend && python -m pytest tests/ -v` → 4 passed in 0.13s.

Tests call the async handlers directly with `asyncio.run` + `pytest.raises(HTTPException)` rather than introducing `httpx` for FastAPI's `TestClient`. Slightly less idiomatic, but avoids a new dependency.

## Known gaps

Deliberately not addressed inside the time-box:

- **In-memory `ITEMS` list with `deepcopy` everywhere.** Replacing the module-level state with a DB session is a rewrite, and the brief explicitly de-scopes "a full database migration." Concurrency safety on the queue would matter once there are multiple workers.
- **Frontend stale-state on action failure.** The new code refetches on success but doesn't roll back if the backend rejects mid-action. Low impact for a single-reviewer instance.
- **Keyboard navigation for the queue.** Genuinely useful for high-volume triage but unbounded scope (focus traps, ARIA, key collisions). Next-step territory.
- **Response models on the FastAPI endpoints.** Declaring `response_model=` would tighten the contract; out of scope here because the priority was workflow correctness.
- **`status_for_action` has an unreachable `"in_review"` fallback.** Cosmetic; left for a code-cleanup pass.

## Files changed and why

- `backend/app/main.py` — strict state-machine guards in `apply_action`, terminal-aware `active_only` filter, urgency-based `queue_order_key`, server-side `CURRENT_REVIEWER` constant.
- `backend/tests/test_smoke.py` — replaced asyncio smoke checks with three behaviour-pinning tests and an autouse reset fixture.
- `frontend/src/App.vue` — `validActions` / `isTerminal` computed, `ACTION_LABELS` map, `v-for` action buttons, empty-state section, refetch-after-action, backend-detail error surfacing.
- `frontend/src/api.ts` — `extractErrorDetail` helper that pulls `detail` from the response body so backend rule messages surface in the UI.
- `.gitignore` — added `.idea/` and `prompt.md` in an off-clock `chore: ignore .idea/ and prompt.md` commit before the 90-minute window started.

## AI assistance used

Two Claude sessions:

1. **External triage session** (out-of-repo, before the timer). I used Claude to triage the brief and codebase against a custom P/T/C prompt of my own design (the prompt itself is now gitignored as `prompt.md`). The session produced a written 6-section triage document and a 90-minute execution plan. I refined the plan three times for accuracy — adding an off-clock cleanup step, reframing the UX improvement as a brief-required deliverable rather than a bonus, and pointing the SUBMISSION.md write-up at the in-repo template. I treated this session as research only; no code was written here.

2. **In-repo implementation session** (during the timer, manual-approve mode). I used Claude as a paired implementer with auto-edit OFF — every diff was reviewed and approved before landing. Each substantive change had a one-line "why" I can defend in the walkthrough. The model proposed edits; I made the decisions on shape, scope, and what to leave alone (see "Known gaps").

I understand and own every line of this submission.
