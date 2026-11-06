"""
AURA Tests — ORM Models.

Tests the database model layer: field defaults, relationships,
enum values, and repr methods.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from app.database.models import (
    AgentRun,
    AgentRunStatus,
    AuditEvent,
    AuditEventType,
    Conversation,
    ConversationStatus,
    Message,
    MessageRole,
    Organization,
    ToolCall,
    ToolCallStatus,
    User,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_organization_defaults(db_session: AsyncSession) -> None:
    """Organization should have sensible defaults."""
    org = Organization(
        name="Test Org",
        slug="test-org",
    )
    db_session.add(org)
    await db_session.flush()

    assert org.id is not None
    assert isinstance(org.id, uuid.UUID)
    assert org.is_active is True
    assert org.settings == {}


@pytest.mark.asyncio
async def test_organization_repr(db_session: AsyncSession) -> None:
    """Organization __repr__ should include id."""
    org = Organization(name="Test", slug="test")
    db_session.add(org)
    await db_session.flush()
    assert "Organization" in repr(org)


@pytest.mark.asyncio
async def test_user_defaults(
    db_session: AsyncSession,
    organization: Organization,
) -> None:
    """User should have correct defaults."""
    user = User(
        organization_id=organization.id,
        email="new@test.com",
        full_name="New User",
    )
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None
    assert user.is_active is True
    pass
    assert user.metadata_ == {}
    assert user.hashed_password is None
    assert user.last_login_at is None


@pytest.mark.asyncio
async def test_conversation_status_enum_values(
    db_session: AsyncSession,
    organization: Organization,
    user: User,
) -> None:
    """All ConversationStatus values should be storable."""
    for status in ConversationStatus:
        conv = Conversation(
            organization_id=organization.id,
            user_id=user.id,
            status=status,
            metadata_={},
        )
        db_session.add(conv)
    await db_session.flush()


@pytest.mark.asyncio
async def test_message_roles(
    db_session: AsyncSession,
    conversation: Conversation,
) -> None:
    """All MessageRole values should be storable."""
    for role in MessageRole:
        msg = Message(
            conversation_id=conversation.id,
            role=role,
            content=f"Test message with role {role}",
            organization_id=conversation.organization_id,
        )
        db_session.add(msg)
    await db_session.flush()


@pytest.mark.asyncio
async def test_agent_run_defaults(
    db_session: AsyncSession,
    conversation: Conversation,
    user: User,
) -> None:
    """AgentRun should initialize with sensible zero-value metrics."""
    run = AgentRun(
        conversation_id=conversation.id,
        user_id=user.id,
        user_request="Test request",
        organization_id=user.organization_id,
    )
    db_session.add(run)
    await db_session.flush()

    assert run.id is not None
    assert run.status == AgentRunStatus.PENDING
    assert run.iteration_count == 0
    assert run.total_tokens_input == 0
    assert run.total_tokens_output == 0
    assert run.estimated_cost_usd is None
    assert run.intent_analysis is None
    assert run.plan is None
    assert run.final_response is None


@pytest.mark.asyncio
async def test_tool_call_defaults(
    db_session: AsyncSession,
    conversation: Conversation,
    user: User,
) -> None:
    """ToolCall should default to PENDING status."""
    run = AgentRun(
        organization_id=conversation.organization_id,
        conversation_id=conversation.id,
        user_id=user.id,
        user_request="Test",
    )
    db_session.add(run)
    await db_session.flush()

    tool_call = ToolCall(
        agent_run_id=run.id,
        tool_name="customer_lookup",
        input_args={"customer_id": "CUST-001"},
    )
    db_session.add(tool_call)
    await db_session.flush()

    assert tool_call.status == ToolCallStatus.PENDING
    assert tool_call.output is None
    assert tool_call.latency_ms is None
    assert tool_call.iteration == 1


@pytest.mark.asyncio
async def test_audit_event_immutable_create(
    db_session: AsyncSession,
    organization: Organization,
    user: User,
) -> None:
    """AuditEvent should be created and persist all fields."""
    event = AuditEvent(
        organization_id=organization.id,
        user_id=user.id,
        event_type=AuditEventType.CONVERSATION_CREATED,
        event_data={"conversation_id": "test-id"},
        request_id="req-12345",
        ip_address="127.0.0.1",
    )
    db_session.add(event)
    await db_session.flush()

    assert event.id is not None
    assert event.event_type == AuditEventType.CONVERSATION_CREATED
    assert event.event_data["conversation_id"] == "test-id"
    assert event.request_id == "req-12345"


@pytest.mark.asyncio
async def test_domain_errors_structure() -> None:
    """Domain errors should have the correct structure and codes."""
    from app.core.errors import (
        AgentTimeoutError,
        NotFoundError,
        ToolExecutionError,
    )

    not_found = NotFoundError("Customer", "CUST-999")
    assert not_found.code == "not_found"
    assert not_found.status_code == 404
    assert "Customer" in not_found.message
    d = not_found.to_dict()
    assert d["error"]["code"] == "not_found"

    tool_err = ToolExecutionError("customer_lookup", "API timeout")
    assert tool_err.code == "tool_execution_error"
    assert "customer_lookup" in tool_err.message
    assert tool_err.details["tool_name"] == "customer_lookup"

    timeout_err = AgentTimeoutError()
    assert timeout_err.code == "agent_timeout"
    assert timeout_err.status_code == 504
