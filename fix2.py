import re

with open('backend/app/database/models.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    '    conversation_id: Mapped[uuid.UUID] = mapped_column(',
    '    organization_id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)\n    conversation_id: Mapped[uuid.UUID] = mapped_column('
)

# wait, I also need to make AgentRun inherit from TimestampMixin! Let's check if it does.
if 'class AgentRun(Base):' in code:
    code = code.replace('class AgentRun(Base):', 'class AgentRun(TimestampMixin, Base):')
if 'class Conversation(Base):' in code:
    code = code.replace('class Conversation(Base):', 'class Conversation(TimestampMixin, Base):')
if 'class AuditEvent(Base):' in code:
    code = code.replace('class AuditEvent(Base):', 'class AuditEvent(TimestampMixin, Base):')

with open('backend/app/database/models.py', 'w', encoding='utf-8') as f:
    f.write(code)
