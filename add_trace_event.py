with open('backend/app/database/models.py', 'r') as f:
    text = f.read()

agent_trace = '''

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

if "AgentTraceEvent" not in text:
    text += agent_trace

with open('backend/app/database/models.py', 'w') as f:
    f.write(text)
