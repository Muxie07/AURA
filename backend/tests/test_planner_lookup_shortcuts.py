"""Lookup shortcuts must never answer an action request with a stored record.

Regression: "...at end_customer tier with 25% discount" matched the customer-history
shortcut because "customer" appears inside the price tier "end_customer". AURA
replayed an old stored invoice (wrong customer, wrong quantity, no discount, an
"APPROVED" label) instead of planning the action, so the approval rule never ran.
"""

import uuid

import pytest

import app.agents.planning.planner as planner
from app.agents.core.state import AgentState
from app.agents.planning.planner import UnderstandNode, _is_action_request

STORED = {
    "invoice_id": "INV-OLD-1",
    "billed_to": {"name": "Northwind Trading"},
    "items": [{"quantity": 12, "model": "UC-2000-VE-4T"}],
    "grand_total": 599676.0,
    "status": "APPROVED",
}

ACTIONS = [
    "Generate an invoice for Acme Technologies for 10 units of UC-2000-VE-4T at end_customer tier with 25% discount",
    "Create a quotation for Acme Technologies for 10 units of UC-2000-VE-4T at end_customer tier with 25% discount",
    "Prepare a quotation for Acme with 30 percent discount",
]
LOOKUPS = [
    "What did Northwind Trading buy?",
    "Show recent invoices on record",
    "tell me about the customer Northwind Trading",
]


@pytest.fixture(autouse=True)
def stored_records(monkeypatch):
    import app.tools.builtin.invoices as inv

    monkeypatch.setattr(inv, "find_stored_invoice", lambda q="": STORED)


async def _run(text: str) -> AgentState:
    state = AgentState(
        run_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        original_request=text,
    )
    return await UnderstandNode(llm_service=None)._execute(state)


@pytest.mark.parametrize("text", ACTIONS)
def test_action_requests_are_recognised(text):
    assert _is_action_request(text)


@pytest.mark.parametrize("text", LOOKUPS + ["I need to generate a Tax Invoice"])
def test_lookups_are_not_actions(text):
    assert not _is_action_request(text)


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ACTIONS)
async def test_action_is_not_answered_from_stored_record(text):
    out = await _run(text)
    assert "Northwind" not in (out.final_response or "")
    assert "Memory on Record" not in (out.final_response or "")


@pytest.mark.asyncio
async def test_real_history_question_still_uses_stored_record():
    out = await _run("What did Northwind Trading buy?")
    assert "Northwind Trading" in (out.final_response or "")
