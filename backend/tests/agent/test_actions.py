import uuid

import pytest

from app.tools.builtin.pricing import pricing_calculate_handler
from app.tools.schemas import ToolContext


@pytest.mark.asyncio
async def test_calculate_quotation_action():
    context = ToolContext(
        organization_id=uuid.uuid4(), agent_run_id=uuid.uuid4(), execution_id="test-1"
    )
    result = await pricing_calculate_handler(
        {"quantity": 500, "base_price": "100.00", "tax_percent": "10", "discount_percent": "0"},
        context,
    )

    assert result["subtotal"] == "50000.0000"
    assert result["tax_amount"] == "5000.0000"
    assert result["total"] == "55000.0000"


@pytest.mark.asyncio
async def test_calculate_quotation_invalid():
    context = ToolContext(
        organization_id=uuid.uuid4(), agent_run_id=uuid.uuid4(), execution_id="test-1"
    )
    with pytest.raises(Exception):
        await pricing_calculate_handler({"quantity": "invalid", "base_price": "100.00"}, context)
