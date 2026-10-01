import uuid

import pytest
import pytest_asyncio

from app.tools.builtin.customers import customer_search_tool
from app.tools.builtin.quotations import quotation_create_draft_tool
from app.tools.errors import ToolExecutionError
from app.tools.schemas import ToolContext


@pytest.fixture
def mock_context():
    return ToolContext(
        organization_id=uuid.UUID("43d85a04-0ba3-4162-b8c0-4611fce533b3"),
        user_id=uuid.uuid4(),
        agent_run_id=uuid.uuid4(),
        execution_id=str(uuid.uuid4()),
    )


@pytest_asyncio.fixture(autouse=True)
async def seed_customers(db_session, mock_context, other_tenant_context):
    from app.database.models import Customer, Product

    c1 = Customer(
        id=str(uuid.uuid4()),
        name="Acme Technologies",
        email="acme@com",
        organization_id=mock_context.organization_id,
    )
    c3 = Customer(
        id=str(uuid.uuid4()),
        name="Acme Other",
        email="acme2@com",
        organization_id=other_tenant_context.organization_id,
    )
    org_id_str1 = str(mock_context.organization_id)[:8]
    org_id_str2 = str(other_tenant_context.organization_id)[:8]
    p1 = Product(
        id=f"PROD-X-{org_id_str1}",
        name="Test Prod",
        sku="SKU-1",
        availability="in_stock",
        base_price=100.0,
        organization_id=mock_context.organization_id,
    )
    p2 = Product(
        id=f"PROD-X-{org_id_str2}",
        name="Test Prod 2",
        sku="SKU-2",
        availability="in_stock",
        base_price=100.0,
        organization_id=other_tenant_context.organization_id,
    )
    db_session.add_all([c1, c3, p1, p2])
    await db_session.commit()


@pytest.fixture
def other_tenant_context():
    return ToolContext(
        organization_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        user_id=uuid.uuid4(),
        agent_run_id=uuid.uuid4(),
        execution_id=str(uuid.uuid4()),
    )


@pytest.mark.asyncio
async def test_quotation_creation_valid(mock_context, client):
    res_cust = await customer_search_tool.execute({"query": "Acme"}, mock_context)
    cust_id = res_cust.result["customers"][0]["id"]
    org_id_str = str(mock_context.organization_id)[:8]

    args = {
        "customer_id": cust_id,
        "items": [{"product_id": f"PROD-X-{org_id_str}", "quantity": 2}],
    }
    res = await quotation_create_draft_tool.execute(args, mock_context)
    assert res.result["status"] == "draft"
    assert res.result["quotation_id"].startswith("Q-")


@pytest.mark.asyncio
async def test_quotation_cross_tenant_customer(mock_context, other_tenant_context, client):
    # Customer belongs to mock_context
    res_cust = await customer_search_tool.execute({"query": "Acme"}, mock_context)
    cust_id = res_cust.result["customers"][0]["id"]
    org_id_str = str(other_tenant_context.organization_id)[:8]

    args = {
        "customer_id": cust_id,
        "items": [{"product_id": f"PROD-X-{org_id_str}", "quantity": 1}],
    }
    # Create quote with other_tenant_context
    with pytest.raises(ToolExecutionError, match="Invalid or unauthorized customer"):
        await quotation_create_draft_tool.execute(args, other_tenant_context)
