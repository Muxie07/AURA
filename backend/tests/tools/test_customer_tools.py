import uuid

import pytest
import pytest_asyncio

from app.tools.builtin.customers import customer_get_tool, customer_search_tool
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
    import sqlalchemy as sa

    from app.database.models import Customer, Organization
    await db_session.execute(sa.text("DELETE FROM customers"))
    await db_session.execute(sa.text("DELETE FROM products"))
    org1 = Organization(id=mock_context.organization_id, name="Org1", slug="org1")
    org2 = Organization(id=other_tenant_context.organization_id, name="Org2", slug="org2")
    await db_session.merge(org1)
    await db_session.merge(org2)
    await db_session.flush()

    c1 = Customer(
    id=str(uuid.uuid4()),
    code="CUST-1",
    name="Acme Technologies",
    email="acme@com",
    organization_id=mock_context.organization_id,
    )
    c2 = Customer(
    id=str(uuid.uuid4()),
    code="CUST-2",
    name="Another com",
    email="another@com",
    organization_id=mock_context.organization_id,
    )
    c3 = Customer(
    id=str(uuid.uuid4()),
    code="CUST-3",
    name="Acme Other",
    email="acme2@com",
    organization_id=other_tenant_context.organization_id,
    )
    db_session.add_all([c1, c2, c3])
    await db_session.flush()


@pytest.fixture
def other_tenant_context():
    return ToolContext(
        organization_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        user_id=uuid.uuid4(),
        agent_run_id=uuid.uuid4(),
        execution_id=str(uuid.uuid4()),
    )


@pytest.mark.asyncio
async def test_existing_customer_search(mock_context, client):
    res = await customer_search_tool.execute({"query": "Acme"}, mock_context)
    assert len(res.result["customers"]) == 1
    assert "Acme" in res.result["customers"][0]["name"]
    assert res.result["customers"][0]["org_id"] == str(mock_context.organization_id)


@pytest.mark.asyncio
async def test_unknown_customer_search(mock_context, client):
    res = await customer_search_tool.execute({"query": "Nonexistent Corp"}, mock_context)
    assert len(res.result["customers"]) == 0


@pytest.mark.asyncio
async def test_cross_tenant_id_get(mock_context, other_tenant_context, client):
    # Get ID from mock_context
    res = await customer_search_tool.execute({"query": "Acme"}, mock_context)
    cust_id = res.result["customers"][0]["id"]

    # Try to access with other tenant
    with pytest.raises(ToolExecutionError, match="not found or access denied"):
        await customer_get_tool.execute({"customer_id": cust_id}, other_tenant_context)


@pytest.mark.asyncio
async def test_invalid_id_get(mock_context, client):
    with pytest.raises(ToolExecutionError, match="not found or access denied"):
        await customer_get_tool.execute({"customer_id": "INVALID-ID"}, mock_context)


@pytest.mark.asyncio
async def test_multiple_matching_customer_search(mock_context, client):
    res = await customer_search_tool.execute({"query": "com"}, mock_context)
    assert len(res.result["customers"]) == 2
