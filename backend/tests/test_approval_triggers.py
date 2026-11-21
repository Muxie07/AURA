"""Which agent actions pause for human approval, and that stated discounts are not lost."""

import uuid

import pytest

from app.agents.execution.decision import extract_discount_percent
from app.policy.engine import PolicyEngine
from app.policy.schemas import PolicyContext, PolicyDecision
from app.tools.schemas import RiskLevel


def _ctx(risk, args=None, perms=("tools:read", "tools:write")):
    return PolicyContext(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        tool_name="t",
        risk_level=risk,
        arguments=args or {},
        permissions=list(perms),
    )


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "Create a quotation for Acme for 10 units of UC-2000-VE-4T at reseller tier with 25% discount",
            25.0,
        ),
        ("quote them with a discount of 30", 30.0),
        ("give 12.5 percent off", 12.5),
        ("Create a quotation for Acme for 10 units of UC-2000-VE-4T at reseller tier", None),
        ("discount of 0%", None),
        ("discount 250%", None),
    ],
)
def test_extract_discount_percent(text, expected):
    assert extract_discount_percent(text) == expected


def test_discount_above_20_requires_approval_even_for_write_tool():
    r = PolicyEngine.evaluate(_ctx(RiskLevel.WRITE, {"discount_percent": 25}))
    assert r.decision == PolicyDecision.REQUIRE_APPROVAL


def test_discount_at_or_below_20_is_auto_allowed():
    r = PolicyEngine.evaluate(_ctx(RiskLevel.WRITE, {"discount_percent": 20}))
    assert r.decision == PolicyDecision.ALLOW


def test_external_side_effect_always_requires_approval():
    r = PolicyEngine.evaluate(_ctx(RiskLevel.EXTERNAL_SIDE_EFFECT))
    assert r.decision == PolicyDecision.REQUIRE_APPROVAL


def test_plain_write_and_read_are_allowed():
    assert PolicyEngine.evaluate(_ctx(RiskLevel.WRITE)).decision == PolicyDecision.ALLOW
    assert PolicyEngine.evaluate(_ctx(RiskLevel.READ)).decision == PolicyDecision.ALLOW


def test_extracted_discount_reaches_the_policy_engine():
    text = "Create a quotation for Acme for 10 units of UC-2000-VE-4T at reseller tier with 25% discount"
    args = {"discount_percent": extract_discount_percent(text)}
    assert (
        PolicyEngine.evaluate(_ctx(RiskLevel.WRITE, args)).decision
        == PolicyDecision.REQUIRE_APPROVAL
    )
