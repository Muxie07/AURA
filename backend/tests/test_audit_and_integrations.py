import uuid
import pytest
from httpx import AsyncClient

from app.services.email_service import EmailNotificationService


@pytest.mark.asyncio
async def test_agents_api_crud(client: AsyncClient, organization, user):
    # 1. List agents
    res = await client.get("/api/v1/agents")
    assert res.status_code == 200
    data = res.json()
    assert "agents" in data
    assert len(data["agents"]) >= 5

    # 2. Create agent
    new_agent = {
        "name": "Custom Test SRE Agent",
        "description": "Performs incident triage and automated health checks.",
        "purpose": "Automated system diagnostics",
        "model_provider": "google",
        "model_name": "gemini-2.5-flash",
        "assigned_tools": ["quotation.calculate_pricing"],
        "risk_tier": "LOW",
    }
    create_res = await client.post("/api/v1/agents", json=new_agent)
    assert create_res.status_code == 201
    created = create_res.json()["agent"]
    agent_id = created["id"]

    # 3. Toggle agent status
    toggle_res = await client.patch(f"/api/v1/agents/{agent_id}/status")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["new_status"] == "PAUSED"

    # 4. Delete agent
    del_res = await client.delete(f"/api/v1/agents/{agent_id}")
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_workflows_api(client: AsyncClient, organization, user):
    # 1. List workflows
    res = await client.get("/api/v1/workflows")
    assert res.status_code == 200
    data = res.json()
    assert len(data["workflows"]) >= 2

    # 2. Execute workflow
    wf_id = data["workflows"][0]["id"]
    exec_res = await client.post("/api/v1/workflows/execute", json={"workflow_id": wf_id})
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert "execution_id" in exec_data
    assert len(exec_data["steps"]) > 0


@pytest.mark.asyncio
async def test_audit_logs_api(client: AsyncClient, organization, user):
    # 1. Get audit logs
    res = await client.get("/api/v1/audit/logs")
    assert res.status_code == 200
    data = res.json()
    assert len(data["logs"]) > 0

    # 2. Filter by severity
    res_warn = await client.get("/api/v1/audit/logs?severity=WARN")
    assert res_warn.status_code == 200

    # 3. Export CSV
    res_csv = await client.get("/api/v1/audit/logs?export=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "TOOL_EXECUTION" in res_csv.text or "event_type" in res_csv.text


@pytest.mark.asyncio
async def test_tenants_api(client: AsyncClient, organization, user):
    # 1. List members
    res = await client.get("/api/v1/tenants/members")
    assert res.status_code == 200
    data = res.json()
    assert len(data["members"]) > 0

    # 2. Invite member
    invite_payload = {
        "name": "Integration Tester",
        "email": "tester@aura.internal",
        "role": "DEVELOPER",
    }
    inv_res = await client.post("/api/v1/tenants/invite", json=invite_payload)
    assert inv_res.status_code == 201
    inv_data = inv_res.json()
    assert inv_data["status"] == "INVITED"


@pytest.mark.asyncio
async def test_mcp_hub_api(client: AsyncClient, organization, user):
    # 1. List servers
    res = await client.get("/api/v1/mcp/servers")
    assert res.status_code == 200
    servers = res.json()["servers"]
    assert len(servers) >= 3

    # 2. Ping server
    s_id = servers[0]["id"]
    ping_res = await client.post(f"/api/v1/mcp/servers/{s_id}/ping")
    assert ping_res.status_code == 200
    assert ping_res.json()["status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_models_api(client: AsyncClient, organization, user):
    # 1. List providers
    res = await client.get("/api/v1/models/providers")
    assert res.status_code == 200
    assert len(res.json()["providers"]) >= 4

    # 2. Test provider health
    test_res = await client.post("/api/v1/models/heuristic/test")
    assert test_res.status_code == 200
    assert test_res.json()["status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_gmail_status_and_diagnostics(client: AsyncClient, organization, user):
    res = await client.get("/api/v1/integrations/gmail/status")
    assert res.status_code == 200
    data = res.json()
    assert "integration" in data
    assert "smtp_host" in data

    diag_res = await client.get("/api/v1/integrations/gmail/diagnostics")
    assert diag_res.status_code == 200


@pytest.mark.asyncio
async def test_email_approval_security_workflow(client: AsyncClient, db_session, conversation):
    import uuid
    from datetime import UTC, datetime, timedelta
    from app.database.models import AgentRun, ApprovalRequest, ApprovalStatus

    # Create an agent run record
    agent_run = AgentRun(
        organization_id=conversation.organization_id,
        conversation_id=conversation.id,
        user_id=conversation.user_id,
        user_request="Security test approval run",
    )
    db_session.add(agent_run)
    await db_session.commit()
    await db_session.refresh(agent_run)

    # Create an approval record
    approval = ApprovalRequest(
        agent_run_id=agent_run.id,
        organization_id=conversation.organization_id,
        tool_name="quotation.create_draft",
        action_summary="Security Test Approval Action",
        action_details={"total": "1000"},
        args_hash="hash_sec_123",
        status=ApprovalStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(approval)
    await db_session.commit()
    await db_session.refresh(approval)

    # Generate token
    token = EmailNotificationService.generate_token(approval.id, "approve")

    # 1. Verify GET request NEVER executes action (Security Requirement)
    get_res = await client.get(f"/api/v1/approvals/email-action?token={token}")
    assert get_res.status_code == 200
    assert "Verify &amp; Authorize Action" in get_res.text or "Authorize" in get_res.text

    # Re-fetch from DB: MUST STILL BE PENDING!
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.PENDING

    # 2. Execute via POST /api/v1/approvals/decide
    post_res = await client.post(
        "/api/v1/approvals/decide",
        json={"token": token, "decision": "approve"},
    )
    assert post_res.status_code == 200
    assert post_res.json()["status"].upper() == "APPROVED"

    # Re-fetch from DB: MUST BE APPROVED!
    import sqlalchemy as sa
    refreshed_app = (await db_session.execute(sa.select(ApprovalRequest).where(ApprovalRequest.id == approval.id))).scalar_one()
    assert refreshed_app.status == ApprovalStatus.APPROVED

    # 3. Replay attack rejection: attempting to use the token again MUST FAIL
    replay_res = await client.post(
        "/api/v1/approvals/decide",
        json={"token": token, "decision": "approve"},
    )
    assert replay_res.status_code == 400
    assert "already been consumed" in replay_res.text or "already actioned" in replay_res.text
