"""Invoices honour a requested discount, are never labelled 'approved', and >20% needs approval."""

import uuid

import pytest

import app.tools.builtin.invoices as inv
from app.policy.engine import PolicyEngine
from app.policy.schemas import PolicyContext, PolicyDecision
from app.tools.schemas import RiskLevel, ToolContext


@pytest.fixture(autouse=True)
def no_disk_writes(monkeypatch):
    monkeypatch.setattr(inv, "save_generated_invoice", lambda data: None)


def _ctx():
    return ToolContext(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        agent_run_id=uuid.uuid4(),
        execution_id=str(uuid.uuid4()),
    )


BASE = {"company_name": "Acme Technologies", "model_number": "UC-2000-VE-4T", "quantity": 10}


@pytest.mark.asyncio
async def test_invoice_without_discount_is_issued_not_approved():
    out = await inv.invoice_generate_handler(BASE, _ctx())
    assert out["status"] == "ISSUED"
    assert out["discount_amount"] == 0
    assert out["subtotal"] == out["list_subtotal"]
    assert out["grand_total"] == round(out["subtotal"] * 1.18, 2)


@pytest.mark.asyncio
async def test_invoice_discount_reduces_taxable_value_and_tax():
    full = await inv.invoice_generate_handler(BASE, _ctx())
    out = await inv.invoice_generate_handler({**BASE, "discount_percent": 25}, _ctx())
    assert out["discount_percent"] == 25
    assert out["discount_amount"] == round(full["list_subtotal"] * 0.25, 2)
    assert out["subtotal"] == round(full["list_subtotal"] * 0.75, 2)
    assert out["gst_18_percent"] == round(out["subtotal"] * 0.18, 2)
    assert out["grand_total"] == round(out["subtotal"] + out["gst_18_percent"], 2)


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [-1, 101, "abc"])
async def test_invoice_rejects_invalid_discount(bad):
    from app.tools.errors import ToolValidationError

    with pytest.raises(ToolValidationError):
        await inv.invoice_generate_handler({**BASE, "discount_percent": bad}, _ctx())


@pytest.mark.parametrize(
    ("pct", "decision"), [(25, PolicyDecision.REQUIRE_APPROVAL), (10, PolicyDecision.ALLOW)]
)
def test_policy_gates_invoice_discount(pct, decision):
    ctx = PolicyContext(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        tool_name="invoice.generate",
        risk_level=RiskLevel.WRITE,
        arguments={**BASE, "discount_percent": pct},
        permissions=["tools:read", "tools:write"],
    )
    assert PolicyEngine.evaluate(ctx).decision == decision
