import uuid

# Fix conversations.py
conv_path = r'backend/app/api/v1/conversations.py'
with open(conv_path, 'r') as f:
    conv_code = f.read()

old_list_conversations = '''    conversations = result.scalars().all()

    # Count messages per conversation (simple subquery)
    items = []
    for conv in conversations:
        msg_count_result = await db.execute(
            select(func.count()).where(Message.conversation_id == conv.id)
        )
        msg_count = msg_count_result.scalar_one()
        items.append(
            ConversationResponse(
                id=conv.id,
                organization_id=conv.organization_id,
                user_id=conv.user_id,
                title=conv.title,
                status=conv.status,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=msg_count)
        )'''

new_list_conversations = '''    # Using scalar subquery for msg_count to avoid N+1 queries
    msg_count_subq = select(func.count(Message.id)).where(Message.conversation_id == Conversation.id).scalar_subquery()
    page_query = page_query.add_columns(msg_count_subq)
    
    result = await db.execute(page_query)
    rows = result.all()

    items = []
    for conv, msg_count in rows:
        items.append(
            ConversationResponse(
                id=conv.id,
                organization_id=conv.organization_id,
                user_id=conv.user_id,
                title=conv.title,
                status=conv.status,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=msg_count)
        )'''

if old_list_conversations in conv_code:
    conv_code = conv_code.replace(old_list_conversations, new_list_conversations)
else:
    print('Could not find old_list_conversations')

with open(conv_path, 'w') as f:
    f.write(conv_code)


# Fix agent.py
agent_path = r'backend/app/api/v1/agent.py'
with open(agent_path, 'r') as f:
    agent_code = f.read()

if 'async def stream_agent_trace(run_id: uuid.UUID, db: DatabaseDep, current_user: CurrentUserDep):' in agent_code:
    agent_code = agent_code.replace(
        'async def stream_agent_trace(run_id: uuid.UUID, db: DatabaseDep, current_user: CurrentUserDep):',
        'from fastapi import Request\n@router.get(\"/agent/runs/{run_id}/stream\")\nasync def stream_agent_trace(run_id: uuid.UUID, db: DatabaseDep, current_user: CurrentUserDep, request: Request):'
    )
    agent_code = agent_code.replace('@router.get(\"/agent/runs/{run_id}/stream\")\nfrom fastapi', 'from fastapi')

if 'await asyncio.sleep(1)' in agent_code:
    agent_code = agent_code.replace(
        'await asyncio.sleep(1)',
        'if await request.is_disconnected():\n                break\n            await asyncio.sleep(1)'
    )

if 'async def list_agent_runs(db: DatabaseDep, current_user: CurrentUserDep) -> Any:' in agent_code:
    agent_code = agent_code.replace(
        'async def list_agent_runs(db: DatabaseDep, current_user: CurrentUserDep) -> Any:',
        'from fastapi import Query\n@router.get(\"/agent/runs\")\nasync def list_agent_runs(db: DatabaseDep, current_user: CurrentUserDep, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)) -> Any:'
    )
    agent_code = agent_code.replace('@router.get(\"/agent/runs\")\nfrom fastapi', 'from fastapi')
    
    old_list_runs_query = '''    runs = await db.scalars(
        sa.select(AgentRun).join(Conversation).where(Conversation.organization_id == current_user.organization_id).order_by(AgentRun.started_at.desc())
    )'''
    new_list_runs_query = '''    runs = await db.scalars(
        sa.select(AgentRun).join(Conversation).where(Conversation.organization_id == current_user.organization_id).order_by(AgentRun.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )'''
    agent_code = agent_code.replace(old_list_runs_query, new_list_runs_query)

if 'async def list_approvals(db: DatabaseDep, current_user: CurrentUserDep) -> Any:' in agent_code:
    agent_code = agent_code.replace(
        'async def list_approvals(db: DatabaseDep, current_user: CurrentUserDep) -> Any:',
        '@router.get(\"/agent/approvals\")\nasync def list_approvals(db: DatabaseDep, current_user: CurrentUserDep, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)) -> Any:'
    )
    agent_code = agent_code.replace('@router.get(\"/agent/approvals\")\n@router.get(\"/agent/approvals\")', '@router.get(\"/agent/approvals\")')
    old_list_approvals_query = '''    approvals = await db.scalars(
        sa.select(ApprovalRequest).join(AgentRun).join(Conversation).where(Conversation.organization_id == current_user.organization_id).order_by(ApprovalRequest.created_at.desc())
    )'''
    new_list_approvals_query = '''    approvals = await db.scalars(
        sa.select(ApprovalRequest).join(AgentRun).join(Conversation).where(Conversation.organization_id == current_user.organization_id).order_by(ApprovalRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )'''
    agent_code = agent_code.replace(old_list_approvals_query, new_list_approvals_query)

with open(agent_path, 'w') as f:
    f.write(agent_code)

print('Done patching.')
