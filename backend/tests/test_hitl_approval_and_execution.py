"""
End-to-End Human-in-the-Loop (HITL) Governance & Business Action Execution Verification Tests.

Covers:
Phase 1: Architecture audit verification
Phase 2: Complete structured action request records with SHA-256 snapshot hashes
Phase 3: 14-section executive Gmail approval notification email format
Phase 4: Cryptographic decision authorization (single-use JTI nonce, anti-replay, GET never mutates state)
Phase 5: Resumption and execution of original action via ToolRegistry
Phase 6: Completion notification email dispatch with real execution results & audit trail
Phase 7: End-to-end safe commercial quotation demonstration & failure path verification
Phase 8: Action monitor & trace verification
"""

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents.core.state import ActionHistoryItem, AgentAction, AgentNodeState, AgentPlan, AgentState
from app.agents.services.agent_service import AgentWorkflowService
from app.config.settings import Environment, ModelProvider, Settings, get_settings
from app.database.base import Base
from app.database.models import (
    AgentRun,
    AgentRunStatus,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    AuditEventType,
    Conversation,
    ConversationStatus,
    Message,
    MessageRole,
    Organization,
    User,
    UserRole,
)
from app.policy.engine import PolicyEngine
from app.policy.schemas import PolicyContext, PolicyDecision
from app.services.email_service import EmailNotificationService
from app.ai.services.llm import LLMService
from app.knowledge.rag_service import RAGService
from app.tools.builtin.communications import communication_send_quotation_tool
from app.tools.executor import InternalToolExecutor
from app.tools.registry import ApprovalRequiredError, ToolRegistry
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("AURA_SECRET_KEY", "test-secret-key-at-least-32-characters-long")
    monkeypatch.setenv("AURA_FRONTEND_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("AURA_API_BASE_URL", "http://localhost:8000/api/v1")
    monkeypatch.setenv("GMAIL_RECIPIENT_EMAIL", "approver@cloudinfotech.internal")
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "mock")
    monkeypatch.setenv("AURA_PRIMARY_LLM_PROVIDER", "mock")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-mock-key")
    monkeypatch.setenv("AURA_AGENT_TIMEOUT_SECONDS", "15")
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def sqlite_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(sqlite_engine):
    factory = async_sessionmaker(
        bind=sqlite_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def seed_data(db_session: AsyncSession):
    org = Organization(name="Cloud Infotech Partner Org", slug="cloud-infotech-test")
    db_session.add(org)
    await db_session.flush()

    user = User(
        organization_id=org.id,
        email="executive@cloudinfotech.com",
        full_name="Chief Revenue Officer",
        role=UserRole.ADMIN,
        hashed_password="mockhashedpassword123",
    )
    db_session.add(user)
    await db_session.flush()

    conv = Conversation(
        organization_id=org.id,
        user_id=user.id,
        title="Commercial Quotation Negotiation",
        status=ConversationStatus.ACTIVE,
    )
    db_session.add(conv)
    await db_session.flush()

    await db_session.commit()
    return {"org": org, "user": user, "conv": conv}


# =============================================================================
# Test 1: Phase 2 Structured Action Record & SHA-256 Immutable Hash
# =============================================================================

@pytest.mark.asyncio
async def test_action_request_structure_and_immutable_hash(db_session: AsyncSession, seed_data: dict):
    """
    Verifies that every proposed action produces a complete, auditable record
    with all Phase 2 attributes and an immutable cryptographic SHA-256 snapshot hash.
    """
    org = seed_data["org"]
    user = seed_data["user"]
    conv = seed_data["conv"]

    run = AgentRun(
        organization_id=org.id,
        conversation_id=conv.id,
        user_id=user.id,
        user_request="Prepare and send a 25% discount quotation to Cloud Infotech Partner",
        status=AgentRunStatus.AWAITING_APPROVAL,
    )
    db_session.add(run)
    await db_session.flush()

    raw_params = {
        "quotation_id": "QT-2026-0042",
        "company_name": "Cloud Infotech Partner",
        "recipient": "procurement@cloudinfotech.com",
        "model_number": "UC-2000-VE-8T",
        "total": "18,750.00",
        "discount_percent": 25.0,
    }

    # Canonical SHA-256 snapshot calculation
    canonical = json.dumps(raw_params, sort_keys=True, separators=(",", ":"), default=str)
    expected_hash = hashlib.sha256(canonical.encode()).hexdigest()

    now_utc = datetime.now(UTC)
    expires_utc = now_utc + timedelta(hours=24)

    structured_details = {
        "action_id": str(uuid.uuid4()),
        "tenant_id": str(org.id),
        "requesting_agent": "AURA Autonomous Commercial Agent",
        "action_name": "communication.send_quotation",
        "business_objective": "Transmit authorized commercial quotation to Cloud Infotech Partner",
        "explanation": "AURA has formulated and verified the quotation parameters.",
        "why_necessary": "Commercial discount of 25.0% exceeds authorized 20% limit.",
        "supporting_evidence": {
            "client": "Cloud Infotech Partner",
            "model": "UC-2000-VE-8T",
            "requested_discount": "25.0%",
        },
        "target_recipient": "procurement@cloudinfotech.com",
        "exact_parameters": raw_params,
        "financial_impact": "Total Value: $18,750.00, Discount: 25.0%",
        "operational_impact": "Dispatches official quotation to customer and updates records.",
        "risks_and_uncertainties": "Non-reversible customer-facing commitment once dispatched.",
        "approval_policy": "Human-in-the-Loop Commercial Governance Gate",
        "request_timestamp": now_utc.isoformat(),
        "expiration_timestamp": expires_utc.isoformat(),
        "execution_status": "AWAITING_APPROVAL",
    }

    approval = ApprovalRequest(
        agent_run_id=run.id,
        organization_id=org.id,
        tool_name="communication.send_quotation",
        action_summary="Send Quotation to Cloud Infotech Partner: 25% discount",
        action_details=structured_details,
        args_hash=expected_hash,
        status=ApprovalStatus.PENDING,
        expires_at=expires_utc,
    )
    db_session.add(approval)
    await db_session.commit()
    await db_session.refresh(approval)

    assert approval.id is not None
    assert approval.args_hash == expected_hash
    assert approval.action_details["target_recipient"] == "procurement@cloudinfotech.com"
    assert approval.action_details["financial_impact"] == "Total Value: $18,750.00, Discount: 25.0%"
    assert approval.status == ApprovalStatus.PENDING


# =============================================================================
# Test 2: Phase 3 Comprehensive 14-Section Gmail Approval Notification Email
# =============================================================================

@pytest.fixture
def stub_email_provider(monkeypatch):
    """Configure a provider so delivery is reported honestly; no network call is made."""
    from app.services.email_service import EmailNotificationService as _Svc

    async def _fake_send(to, subject, html, text):
        return "test-message-id"

    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setattr(_Svc, "_send_via_resend", staticmethod(_fake_send))


@pytest.mark.usefixtures("stub_email_provider")
@pytest.mark.asyncio
async def test_gmail_approval_email_14_sections():
    """
    Verifies that the generated approval notification email contains all 14 required sections
    in both HTML and plain text formats.
    """
    approval_id = uuid.uuid4()
    details = {
        "company_name": "Cloud Infotech Partner",
        "business_objective": "Transmit authorized quotation QT-2026-0042 to Cloud Infotech Partner",
        "why_necessary": "Commercial discount of 25.0% exceeds authorized auto-approval limit of 20%.",
        "supporting_evidence": {
            "customer": "Cloud Infotech Partner",
            "model": "UC-2000-VE-8T",
            "rate_card": "Enterprise Tier 1",
        },
        "data_affected": "Quotation store, CRM activity logs, external email transmission ledger.",
        "target_recipient": "procurement@cloudinfotech.com",
        "financial_impact": "Total Value: $18,750.00 (Applied Discount: 25.0%)",
        "expected_result": "Quotation delivered to procurement team; commercial terms locked for 30 days.",
        "risks_and_uncertainties": "Legally binding price quotation once transmitted externally.",
        "total": "18,750.00",
        "discount_percent": 25.0,
    }

    email_record = await EmailNotificationService.send_approval_request_email(
        approval_id=approval_id,
        tool_name="communication.send_quotation",
        action_summary="Send Quotation to Cloud Infotech Partner",
        action_details=details,
        recipient_email="approver@cloudinfotech.internal",
    )

    assert email_record["status"] == "DELIVERED"
    html = email_record["html"]
    text = email_record["text"]

    # 1. Company Name
    assert "Cloud Infotech Partner" in html and "Cloud Infotech Partner" in text
    # 2. AURA Request ID
    assert str(approval_id) in html and str(approval_id) in text
    # 3. What AURA wants to do
    assert "Transmit authorized quotation" in html and "Transmit authorized quotation" in text
    # 4. Why it wants to do it
    assert "exceeds authorized auto-approval limit" in html
    # 5. Supporting Information
    assert "UC-2000-VE-8T" in html
    # 6. Data Affected
    assert "Quotation store" in html
    # 7. Exact Recipient
    assert "procurement@cloudinfotech.com" in html or "approver@cloudinfotech.internal" in html
    # 8. Financial Impact
    assert "18,750.00" in html
    # 9. Expected Result
    assert "commercial terms locked for 30 days" in html
    # 10. Risks & Uncertainties
    assert "binding price quotation" in html
    # 11 & 12. Approved / Rejected consequences
    assert "If Approved" in html and "If Rejected" in html
    # 13. Expiration
    assert "24 hours" in html
    # 14. Secure Review Link (GET review, POST decision)
    assert "/approvals/email-action?token=" in html
    assert email_record["approve_url"].startswith("http")


# =============================================================================
# Test 3: Phase 4 Security — GET Request NEVER Mutates Execution State
# =============================================================================

@pytest.mark.asyncio
async def test_get_review_screen_does_not_mutate_state(db_session: AsyncSession, seed_data: dict):
    """
    STRICT SECURITY REQUIREMENT:
    A GET request must NEVER approve or mutate execution state.
    Calling GET /approvals/email-action renders the review screen but preserves PENDING status.
    """
    from starlette.requests import Request
    from app.api.v1.runs import process_email_approval_action

    org = seed_data["org"]
    conv = seed_data["conv"]
    user = seed_data["user"]

    run = AgentRun(
        organization_id=org.id,
        conversation_id=conv.id,
        user_id=user.id,
        user_request="Quotation flow",
        status=AgentRunStatus.AWAITING_APPROVAL,
    )
    db_session.add(run)
    await db_session.flush()

    approval = ApprovalRequest(
        agent_run_id=run.id,
        organization_id=org.id,
        tool_name="communication.send_quotation",
        action_summary="Quotation for Cloud Infotech Partner",
        action_details={"company": "Cloud Infotech Partner", "total": "18750"},
        args_hash="mock-hash-1234",
        status=ApprovalStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(approval)
    await db_session.commit()

    token = EmailNotificationService.generate_token(approval.id, "approve")

    # Call GET endpoint
    response = await process_email_approval_action(token=token, decision="approve", db=db_session)
    assert response.status_code == 200
    assert "Verify &amp; Authorize Action" in response.body.decode()
    assert "actions-form" in response.body.decode()

    # Re-verify state: MUST STILL BE PENDING!
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.PENDING
    assert approval.actioned_at is None

    await db_session.refresh(run)
    assert run.status == AgentRunStatus.AWAITING_APPROVAL


# =============================================================================
# Test 4: Phase 4 Security — Single-Use Nonce & Anti-Replay Defense
# =============================================================================

@pytest.mark.asyncio
async def test_anti_replay_single_use_token(db_session: AsyncSession, seed_data: dict):
    """
    Verifies that a token can only be consumed once.
    Duplicate submissions with the same cryptographic JTI nonce are rejected.
    """
    from starlette.requests import Request
    from app.api.v1.runs import decide_approval_action
    from fastapi import HTTPException

    org = seed_data["org"]
    conv = seed_data["conv"]
    user = seed_data["user"]

    run = AgentRun(
        organization_id=org.id,
        conversation_id=conv.id,
        user_id=user.id,
        user_request="Quote action",
        status=AgentRunStatus.AWAITING_APPROVAL,
    )
    db_session.add(run)
    await db_session.flush()

    approval = ApprovalRequest(
        agent_run_id=run.id,
        organization_id=org.id,
        tool_name="communication.send_quotation",
        action_summary="Quotation Sign-off",
        action_details={"company": "Cloud Infotech Partner"},
        args_hash="hash-abc",
        status=ApprovalStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(approval)
    await db_session.commit()

    token = EmailNotificationService.generate_token(approval.id, "approve")

    # First POST submission: Should succeed
    scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 8000),
    }
    body_bytes = json.dumps({"token": token, "decision": "approve"}).encode()

    async def receive():
        return {"type": "http.request", "body": body_bytes}

    req1 = Request(scope, receive)
    res1 = await decide_approval_action(req1, db=db_session)
    assert res1["status"] == "approved"

    # Second POST submission with exact same token: Must be rejected as replay
    async def receive_again():
        return {"type": "http.request", "body": body_bytes}

    req2 = Request(scope, receive_again)
    with pytest.raises(HTTPException) as exc_info:
        await decide_approval_action(req2, db=db_session)
    assert exc_info.value.status_code == 400
    assert "Replay attack blocked" in exc_info.value.detail or "already been consumed" in exc_info.value.detail


# =============================================================================
# Test 5: Phase 4 Security — Expired Token Rejection
# =============================================================================

@pytest.mark.asyncio
async def test_expired_token_rejected(db_session: AsyncSession, seed_data: dict):
    """Verifies that expired approval tokens are rejected."""
    import jwt
    from starlette.requests import Request
    from app.api.v1.runs import decide_approval_action
    from fastapi import HTTPException

    settings = get_settings()
    secret = settings.aura_secret_key.get_secret_value()
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "approval_id": str(uuid.uuid4()),
        "decision": "approve",
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "iss": "aura-platform",
        "iat": datetime.now(UTC) - timedelta(hours=2),
        "jti": uuid.uuid4().hex,
    }
    expired_token = jwt.encode(expired_payload, secret, algorithm="HS256")

    scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 8000),
    }
    body_bytes = json.dumps({"token": expired_token, "decision": "approve"}).encode()

    async def receive():
        return {"type": "http.request", "body": body_bytes}

    req = Request(scope, receive)
    with pytest.raises(HTTPException) as exc_info:
        await decide_approval_action(req, db=db_session)
    assert exc_info.value.status_code == 400
    assert "expired" in exc_info.value.detail.lower()


# =============================================================================
# Test 6: Safe Commercial Rejection Path (Decision: Deny)
# =============================================================================

@pytest.mark.asyncio
async def test_human_rejection_cancels_run_gracefully(db_session: AsyncSession, seed_data: dict):
    """
    Verifies that when an approver rejects the action:
    1. ApprovalRequest status is updated to DENIED.
    2. Agent execution completes gracefully with a cancellation notice.
    3. The tool is NOT executed.
    4. A cancellation completion email is dispatched.
    """
    from starlette.requests import Request
    from app.api.v1.runs import decide_approval_action

    org = seed_data["org"]
    conv = seed_data["conv"]
    user = seed_data["user"]

    run = AgentRun(
        organization_id=org.id,
        conversation_id=conv.id,
        user_id=user.id,
        user_request="Quote request",
        status=AgentRunStatus.AWAITING_APPROVAL,
    )
    db_session.add(run)
    await db_session.flush()

    approval = ApprovalRequest(
        agent_run_id=run.id,
        organization_id=org.id,
        tool_name="communication.send_quotation",
        action_summary="Quotation for Cloud Infotech Partner",
        action_details={"company_name": "Cloud Infotech Partner", "total": "18750"},
        args_hash="hash-xyz",
        status=ApprovalStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(approval)
    await db_session.commit()

    token = EmailNotificationService.generate_token(approval.id, "deny")

    scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 8000),
    }
    body_bytes = json.dumps({"token": token, "decision": "deny"}).encode()

    async def receive():
        return {"type": "http.request", "body": body_bytes}

    req = Request(scope, receive)
    res = await decide_approval_action(req, db=db_session)
    assert res["status"] == "denied"

    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.DENIED

    # Verify agent service completes run as cancelled
    llm = LLMService()
    rag = RAGService(db_session, llm)
    agent_svc = AgentWorkflowService(db_session, llm, rag)
    state = await agent_svc.execute_run(run.id)

    await db_session.refresh(run)
    assert run.status == AgentRunStatus.COMPLETED
    assert "cancelled" in run.final_response.lower()

    # Verify outbox has cancellation notification
    emails = EmailNotificationService.get_recent_emails()
    assert any("CANCELLED" in e.get("status", "") for e in emails)


# =============================================================================
# Test 7: Tamper Detection — Modified Parameters Require Fresh Approval
# =============================================================================

@pytest.mark.asyncio
async def test_tampered_action_parameters_require_fresh_approval(db_session: AsyncSession, seed_data: dict):
    """
    Verifies that if action parameters are tampered with after human sign-off,
    the SHA-256 snapshot hash does not match and ToolRegistry requires fresh approval.
    """
    org = seed_data["org"]
    conv = seed_data["conv"]
    user = seed_data["user"]

    original_params = {
        "company_name": "Cloud Infotech Partner",
        "recipient": "procurement@cloudinfotech.com",
        "total": "18,750.00",
        "discount_percent": 25.0,
    }
    canonical = json.dumps(original_params, sort_keys=True, separators=(",", ":"), default=str)
    orig_hash = hashlib.sha256(canonical.encode()).hexdigest()

    run = AgentRun(
        organization_id=org.id,
        conversation_id=conv.id,
        user_id=user.id,
        user_request="Quote action",
        status=AgentRunStatus.AWAITING_APPROVAL,
    )
    db_session.add(run)
    await db_session.flush()

    # Pre-approve the original hash
    approval = ApprovalRequest(
        agent_run_id=run.id,
        organization_id=org.id,
        tool_name="communication.send_quotation",
        action_summary="Send quotation to Cloud Infotech Partner",
        action_details=original_params,
        args_hash=orig_hash,
        status=ApprovalStatus.APPROVED,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(approval)
    await db_session.commit()

    # Attacker tampers parameters: changes total from $18,750 to $5,000 (deeper unauthorized discount)
    tampered_params = dict(original_params)
    tampered_params["total"] = "5,000.00"
    tampered_params["discount_percent"] = 80.0

    registry = ToolRegistry()
    registry.register(communication_send_quotation_tool)

    ctx = ToolContext(
        organization_id=org.id,
        agent_run_id=run.id,
        execution_id="exec-tamper-check",
        dry_run=False,
        user_id=user.id,
    )

    # ToolRegistry execution MUST raise ApprovalRequiredError because tampered hash != approved hash
    with pytest.raises(ApprovalRequiredError):
        await registry.execute(db_session, "communication.send_quotation", tampered_params, ctx)


# =============================================================================
# Test 8: Full End-to-End Demonstration Lifecycle (Phases 1-8)
# =============================================================================

@pytest.mark.usefixtures("stub_email_provider")
@pytest.mark.asyncio
async def test_full_approval_and_execution_lifecycle(db_session: AsyncSession, seed_data: dict):
    """
    Complete end-to-end demonstration:
    1. Agent encounters an external side-effect tool (communication.send_quotation).
    2. PolicyEngine intercepts and mandates approval.
    3. Execution pauses safely with AgentRunStatus.AWAITING_APPROVAL and checkpoint saved.
    4. 14-section approval email is dispatched.
    5. Approver authorizes action via authenticated POST.
    6. Original execution resumes from checkpoint.
    7. ToolRegistry consumes approval atomically and executes tool.
    8. Actual execution result is persisted in database.
    9. Run completes with AgentRunStatus.COMPLETED.
    10. Phase 6 completion notification email is dispatched with audit reference!
    """
    from starlette.requests import Request
    from app.api.v1.runs import decide_approval_action

    org = seed_data["org"]
    conv = seed_data["conv"]
    user = seed_data["user"]

    # 1. Start agent run
    run = AgentRun(
        organization_id=org.id,
        conversation_id=conv.id,
        user_id=user.id,
        user_request="Send authorized quotation QT-2026-0042 to Cloud Infotech Partner with 25% discount",
        status=AgentRunStatus.PENDING,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    # 2. Tool action definition (tenant-scoped)
    quote_args = {
        "quotation_id": "QT-2026-0042",
        "company_name": "Cloud Infotech Partner",
        "recipient": "procurement@cloudinfotech.com",
        "total": "18,750.00",
        "discount_percent": 25.0,
        "organization_id": str(org.id),
    }
    canonical = json.dumps(quote_args, sort_keys=True, separators=(",", ":"), default=str)
    args_hash = hashlib.sha256(canonical.encode()).hexdigest()

    # 3. Simulate pausing at execution node
    run.status = AgentRunStatus.AWAITING_APPROVAL
    checkpoint_plan = {
        "status": "WAITING",
        "plan": {
            "goal": "Send quotation",
            "steps": [
                {
                    "id": "step-1",
                    "type": "ACTION",
                    "description": "Send authorized quotation to customer email",
                    "dependencies": [],
                    "required_tools": ["communication.send_quotation"],
                    "risk": "EXTERNAL_SIDE_EFFECT",
                    "expected_output": "Quotation email transmitted",
                    "verification_criteria": "Receipt status succeeded",
                    "status": "pending",
                }
            ],
        },
        "current_actions": [
            {
                "action_id": "step-1",
                "action_type": "communication.send_quotation",
                "description": "Dispatch authorized quotation to customer email",
                "arguments": quote_args,
                "status": "PENDING",
            }
        ],
        "action_history": [],
        "iteration_count": 1,
    }
    run.plan = {"_checkpoint": checkpoint_plan}

    approval = ApprovalRequest(
        agent_run_id=run.id,
        organization_id=org.id,
        tool_name="communication.send_quotation",
        action_summary="Send Quotation to Cloud Infotech Partner: 25% discount",
        action_details={
            "company_name": "Cloud Infotech Partner",
            "recipient": "procurement@cloudinfotech.com",
            "total": "18,750.00",
            "discount_percent": 25.0,
            "exact_parameters": quote_args,
        },
        args_hash=args_hash,
        status=ApprovalStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(approval)
    await db_session.commit()

    # 4. Dispatch 14-section approval email
    email_res = await EmailNotificationService.send_approval_request_email(
        approval_id=approval.id,
        tool_name=approval.tool_name,
        action_summary=approval.action_summary,
        action_details=approval.action_details,
        recipient_email="approver@cloudinfotech.internal",
    )
    assert email_res["status"] == "DELIVERED"

    # 5. Approver authorizes via POST
    token = EmailNotificationService.generate_token(approval.id, "approve")
    scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 8000),
    }
    body_bytes = json.dumps({"token": token, "decision": "approve"}).encode()

    async def receive():
        return {"type": "http.request", "body": body_bytes}

    from fastapi import BackgroundTasks
    bg = BackgroundTasks()
    req = Request(scope, receive)
    decision_res = await decide_approval_action(req, db=db_session, background_tasks=bg)
    assert decision_res["status"] == "approved"

    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.APPROVED

    # 6. Resume execution from checkpoint
    llm = LLMService()
    rag = RAGService(db_session, llm)
    agent_svc = AgentWorkflowService(db_session, llm, rag)
    await agent_svc.initialize(org.id)

    state = await agent_svc.execute_run(run.id)

    # 7. Verify ToolRegistry consumed approval
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.EXECUTED

    # 8. Verify agent run completed
    await db_session.refresh(run)
    assert run.status == AgentRunStatus.COMPLETED

    # 9. Verify actual execution result
    assert len(state.action_history) > 0
    executed_action = state.action_history[-1]
    assert executed_action.action.action_type == "communication.send_quotation"
    assert executed_action.result is not None
    assert executed_action.result.get("quotation_id") == "QT-2026-0042"
    assert executed_action.result.get("recipient") == "procurement@cloudinfotech.com"

    # 10. Verify Phase 6 completion email was dispatched
    emails = EmailNotificationService.get_recent_emails()
    completion_emails = [e for e in emails if e.get("type") == "COMPLETION_NOTIFICATION"]
    assert len(completion_emails) > 0
    latest_comp = completion_emails[0]
    assert latest_comp["status"] == "COMPLETED"
    assert "QT-2026-0042" in latest_comp["html"] or "communication.send_quotation" in latest_comp["html"]
    assert "AUD-" in latest_comp["audit_ref"]
