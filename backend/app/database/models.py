"""
AURA Database Models.

Defines all SQLAlchemy ORM models for Phase 1.

Design decisions:
- UUIDs as primary keys: globally unique, safe for distributed systems
- Soft deletes via is_active flag: preserves audit trail
- Explicit foreign keys with cascade rules
- JSON columns for flexible metadata storage
- pgvector-ready (embeddings column defined but populated in Phase 5)
"""

from __future__ import annotations

import uuid
from datetime import (  # runtime import required by SQLAlchemy Mapped[] scanning
    UTC,
    datetime,
)
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

# ---------------------------------------------------------------------------
# Dialect-agnostic type helpers
# Use sa.JSON for ORM columns — works on PostgreSQL, SQLite, and all backends.
# The Alembic migration uses JSONB explicitly for production PostgreSQL.
# SQLAlchemy 2.0+ generic Uuid works on both PostgreSQL and SQLite (tests).
# ---------------------------------------------------------------------------
_UUID_TYPE = sa.Uuid(as_uuid=True)
_JSON_TYPE = sa.JSON


# =============================================================================
# Enumerations
# =============================================================================


class ConversationStatus(StrEnum):
    """Lifecycle state of a conversation."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    FAILED = "failed"


class MessageRole(StrEnum):
    """Role of a message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class AgentRunStatus(StrEnum):
    """Execution state of an agent run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class UserRole(StrEnum):
    """RBAC Role for a user."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

class APIKey(Base):
    """Service-to-service API keys for an organization."""
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    TIMED_OUT = "timed_out"
    AWAITING_APPROVAL = "awaiting_approval"
    CANCELLED = "cancelled"


class ToolCallStatus(StrEnum):
    """Execution result of a tool call."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    AWAITING_APPROVAL = "awaiting_approval"


class AuditEventType(StrEnum):
    """Categories of auditable events."""

    # Authentication
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_CREATED = "user.created"

    # Conversations
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_COMPLETED = "conversation.completed"

    # Agent
    AGENT_RUN_STARTED = "agent.run_started"
    AGENT_RUN_COMPLETED = "agent.run_completed"
    AGENT_RUN_FAILED = "agent.run_failed"

    # Tools
    TOOL_EXECUTED = "tool.executed"
    TOOL_FAILED = "tool.failed"

    # Approvals
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"

    # Data
    DOCUMENT_INGESTED = "document.ingested"


class ApprovalStatus(StrEnum):
    """State of a pending approval."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


# =============================================================================
# Models
# =============================================================================


class Organization(Base):
    """
    Tenant model. All data is scoped to an organization.

    Supports multi-tenancy for future SaaS deployment.
    """

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        primary_key=True,
        default=uuid.uuid4,
        doc="Organization unique identifier.",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Organization display name.",
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        doc="URL-safe unique identifier.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Soft delete flag.",
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        _JSON_TYPE,
        default=dict,
        nullable=False,
        doc="Organization-level settings (billing tier, feature flags, etc.).",
    )

    # Relationships
    users: Mapped[list[User]] = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    knowledge_bases: Mapped[list[KnowledgeBase]] = relationship(
        "KnowledgeBase",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    __table_args__ = ()


class User(Base):
    """
    User account. Scoped to an organization.

    Authentication details (hashed passwords, OAuth tokens) are stored here.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(320),  # RFC 5321 max email length
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(500), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        doc="BCrypt hash. Null if using SSO.",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            name="user_role_enum",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=UserRole.MEMBER,
        nullable=False,
        server_default="member"
    )

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _JSON_TYPE,
        default=dict,
        nullable=False,
        doc="Flexible user metadata (preferences, avatar URL, etc.).",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization", back_populates="users")
    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation",
        back_populates="user",
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(
        "AuditEvent",
        back_populates="user",
    )

    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_users_org_email"),)


class Conversation(Base):
    """
    A conversation thread between a user and AURA.

    One conversation may contain multiple messages and multiple agent runs.
    Supports multi-turn interactions.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Auto-generated or user-provided conversation title.",
    )
    status: Mapped[ConversationStatus] = mapped_column(
        SAEnum(
            ConversationStatus,
            name="conversation_status_enum",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ConversationStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _JSON_TYPE,
        default=dict,
        nullable=False,
    )

    # Relationships
    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="conversations",
    )
    user: Mapped[User] = relationship("User", back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    agent_runs: Mapped[list[AgentRun]] = relationship(
        "AgentRun",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AgentRun.created_at",
    )

    __table_args__ = ()


class Message(Base):
    """
    A single message in a conversation.

    Stores both user messages and assistant/tool responses.
    """

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        SAEnum(
            MessageRole,
            name="message_role_enum",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Message text content.",
    )
    # Structured content for rich messages (tool results, citations, etc.)
    structured_content: Mapped[dict[str, Any] | None] = mapped_column(
        _JSON_TYPE,
        nullable=True,
        doc="Optional structured payload (citations, tool output summaries, etc.).",
    )
    # Link to the agent run that produced this message (if assistant/tool message)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        _UUID_TYPE,
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Approximate token count for cost tracking.",
    )

    # Relationships
    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")
    agent_run: Mapped[AgentRun | None] = relationship("AgentRun", back_populates="messages")

    __table_args__ = ()


class AgentRun(Base):
    """
    A single execution of the AURA agent in response to a user request.

    Captures the full execution trace: plan, tools called, result, metrics.
    Serves as the primary observability record for agent executions.
    """

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status & Lifecycle
    status: Mapped[AgentRunStatus] = mapped_column(
        SAEnum(
            AgentRunStatus,
            name="agent_run_status_enum",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AgentRunStatus.PENDING,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    # Input
    user_request: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="The original user request that triggered this run.",
    )

    # Execution Trace
    intent_analysis: Mapped[dict[str, Any] | None] = mapped_column(
        _JSON_TYPE,
        nullable=True,
        doc="Structured output from the intent analysis step.",
    )
    plan: Mapped[dict[str, Any] | None] = mapped_column(
        _JSON_TYPE,
        nullable=True,
        doc="Agent execution plan (steps, tools selected).",
    )
    final_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Final natural-language response to the user.",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Error description if status is FAILED.",
    )

    # Metrics
    iteration_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    task_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    selected_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    replans: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    total_tokens_input: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_tokens_output: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    estimated_cost_usd: Mapped[float | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Configuration snapshot (for reproducibility)
    model_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    conversation: Mapped[Conversation] = relationship(
        "Conversation",
        back_populates="agent_runs",
    )
    user: Mapped[User] = relationship("User")
    messages: Mapped[list[Message]] = relationship("Message", back_populates="agent_run")
    tool_calls: Mapped[list[ToolCall]] = relationship(
        "ToolCall",
        back_populates="agent_run",
        cascade="all, delete-orphan",
        order_by="ToolCall.created_at",
    )
    approvals: Mapped[list[ApprovalRequest]] = relationship(
        "ApprovalRequest",
        back_populates="agent_run",
        cascade="all, delete-orphan",
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(
        "AuditEvent",
        back_populates="agent_run",
    )

    __table_args__ = ()


class ToolCall(Base):
    """
    Records a single tool invocation by the agent during a run.

    Captures inputs, outputs, timing, and success/failure for each tool call.
    """

    __tablename__ = "tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Tool identification
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tool_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Execution
    status: Mapped[ToolCallStatus] = mapped_column(
        SAEnum(
            ToolCallStatus,
            name="tool_call_status_enum",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ToolCallStatus.PENDING,
        nullable=False,
        index=True,
    )
    iteration: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Which agent iteration this tool was called in.",
    )

    # Input / Output (stored as _JSON_TYPE)
    input_args: Mapped[dict[str, Any]] = mapped_column(
        _JSON_TYPE,
        default=dict,
        nullable=False,
        doc="Arguments passed to the tool.",
    )
    output: Mapped[dict[str, Any] | None] = mapped_column(
        _JSON_TYPE,
        nullable=True,
        doc="Tool execution result.",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Approval link (if this tool call required approval)
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        _UUID_TYPE,
        ForeignKey("approval_requests.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    agent_run: Mapped[AgentRun] = relationship("AgentRun", back_populates="tool_calls")
    approval: Mapped[ApprovalRequest | None] = relationship(
        "ApprovalRequest",
        foreign_keys=[approval_id],
    )

    __table_args__ = ()


class ApprovalRequest(Base):
    """
    Human-in-the-loop approval request.

    Created when the agent attempts a high-impact action that requires
    explicit user approval before execution.
    """

    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # What action is being requested
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    action_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Human-readable description of the action requiring approval.",
    )
    action_details: Mapped[dict[str, Any]] = mapped_column(
        _JSON_TYPE,
        default=dict,
        nullable=False,
        doc="Structured details for the approval UI (diff, preview data, etc.).",
    )

    # Status
    status: Mapped[ApprovalStatus] = mapped_column(
        SAEnum(
            ApprovalStatus,
            name="approval_status_enum",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ApprovalStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Who actioned it (if actioned)
    actioned_by_id: Mapped[uuid.UUID | None] = mapped_column(
        _UUID_TYPE,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actioned_at: Mapped[datetime | None] = mapped_column(nullable=True)
    denial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Expiry (unapproved requests expire)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    agent_run: Mapped[AgentRun] = relationship("AgentRun", back_populates="approvals")
    actioned_by: Mapped[User | None] = relationship("User", foreign_keys=[actioned_by_id])
    organization: Mapped[Organization] = relationship("Organization")

    __table_args__ = ()


class AuditEvent(Base):
    """
    Immutable audit log record.

    Every significant operation in AURA creates an audit event.
    These records must never be modified or deleted.
    """

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        _UUID_TYPE,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        _UUID_TYPE,
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Event classification
    event_type: Mapped[AuditEventType] = mapped_column(
        SAEnum(
            AuditEventType,
            name="audit_event_type_enum",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )

    # Structured event payload
    event_data: Mapped[dict[str, Any]] = mapped_column(
        _JSON_TYPE,
        default=dict,
        nullable=False,
        doc="Full event context (before/after state, relevant identifiers, etc.).",
    )

    # Request context for traceability
    request_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="HTTP request ID that triggered this event.",
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    user: Mapped[User | None] = relationship("User", back_populates="audit_events")
    agent_run: Mapped[AgentRun | None] = relationship("AgentRun", back_populates="audit_events")

    __table_args__ = ()


# =============================================================================
# Knowledge Management (Phase 3)
# =============================================================================


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    # Relationships
    organization: Mapped[Organization] = relationship(back_populates="knowledge_bases")
    documents: Mapped[list[Document]] = relationship(
        back_populates="knowledge_base", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_latest: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False, index=True)
    indexed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=DocumentStatus.UPLOADED,
        index=True,
    )

    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", _JSON_TYPE, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    # Relationships
    knowledge_base: Mapped[KnowledgeBase] = relationship(back_populates="documents")
    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )

    chunk_index: Mapped[int] = mapped_column(Integer, index=True)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", _JSON_TYPE, default=dict)

    # 1536 matches OpenAI text-embedding-3-small
    embedding: Mapped[Any] = mapped_column(Vector(1536), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    # Relationships
    document: Mapped[Document] = relationship(back_populates="chunks")


class ToolExecutionAudit(Base):
    __tablename__ = "tool_execution_audits"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    execution_id: Mapped[str] = mapped_column(String(100), index=True)
    tool_name: Mapped[str] = mapped_column(String(255), index=True)
    tool_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(50))
    risk_level: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    input_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentTraceEvent(Base):
    __tablename__ = "agent_trace_events"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    component: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        _JSON_TYPE,
        nullable=True,
    )


class MemoryScope(StrEnum):
    RUN = "run"
    CONVERSATION = "conversation"
    ORGANIZATION = "organization"


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True, index=True
    )

    scope: Mapped[MemoryScope] = mapped_column(
        SAEnum(MemoryScope, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(255), index=True)
    content: Mapped[dict[str, Any]] = mapped_column(_JSON_TYPE, default=dict)

    expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class EvalDataset(Base):
    __tablename__ = "eval_datasets"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    examples: Mapped[list[EvalExample]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    runs: Mapped[list[EvalRun]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class EvalExample(Base):
    __tablename__ = "eval_examples"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("eval_datasets.id", ondelete="CASCADE"), index=True
    )

    input_prompt: Mapped[str] = mapped_column(Text)
    expected_tools: Mapped[list[str]] = mapped_column(_JSON_TYPE, default=list)
    expected_output_contains: Mapped[list[str]] = mapped_column(_JSON_TYPE, default=list)
    must_not_contain: Mapped[list[str]] = mapped_column(_JSON_TYPE, default=list)

    is_attack: Mapped[bool] = mapped_column(Boolean, default=False)
    attack_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    dataset: Mapped[EvalDataset] = relationship(back_populates="examples")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("eval_datasets.id", ondelete="CASCADE"), index=True
    )

    model: Mapped[str] = mapped_column(String(100), index=True)
    provider: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", nullable=False
    )

    success_rate: Mapped[float] = mapped_column(sa.Float, default=0.0)
    avg_latency_ms: Mapped[float] = mapped_column(sa.Float, default=0.0)
    avg_tokens: Mapped[float] = mapped_column(sa.Float, default=0.0)
    avg_cost_usd: Mapped[float] = mapped_column(sa.Float, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)

    completed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    dataset: Mapped[EvalDataset] = relationship(back_populates="runs")
    results: Mapped[list[EvalResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("eval_runs.id", ondelete="CASCADE"), index=True
    )
    example_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("eval_examples.id", ondelete="CASCADE"), index=True
    )

    actual_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools_used: Mapped[list[str]] = mapped_column(_JSON_TYPE, default=list)

    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(sa.Float, default=0.0)

    run: Mapped[EvalRun] = relationship(back_populates="results")


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))


class Product(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    sku: Mapped[str] = mapped_column(String(100))
    availability: Mapped[str] = mapped_column(String(50))
    base_price: Mapped[float] = mapped_column(sa.Float, default=0.0)


class Quotation(Base):
    __tablename__ = "quotations"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    items: Mapped[list[dict[str, Any]]] = mapped_column(_JSON_TYPE, default=list)
    total: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
