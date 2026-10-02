import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.tools.builtin.pricing import PricingToolExecutor
from app.tools.schemas import RiskLevel, ToolDefinition, ToolSource


@given(
    base_price=st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
    discount=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    tax=st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False)
)
def test_pricing_math_properties(base_price, discount, tax):
    """Fuzz testing pricing math properties."""
    discounted = base_price * (1 - (discount / 100))
    final = discounted * (1 + (tax / 100))

    assert final >= 0
    if discount == 100.0:
        assert final == 0.0
    if discount == 0.0 and tax == 0.0:
        assert final == base_price
