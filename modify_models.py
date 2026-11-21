with open('backend/app/database/models.py', 'r') as f:
    text = f.read()

models = '''

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    arguments_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(
        SAEnum(ApprovalStatus, name="approval_status_enum", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=ApprovalStatus.PENDING,
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)


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
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        _JSON_TYPE,
        nullable=True,
    )
'''

if "ApprovalRequest" not in text:
    text += models

text = text.replace('    iteration_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)', 
'''    iteration_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    task_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    selected_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    replans: Mapped[int] = mapped_column(Integer, default=0, nullable=False)''')

with open('backend/app/database/models.py', 'w') as f:
    f.write(text)
