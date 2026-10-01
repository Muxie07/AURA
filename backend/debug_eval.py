import asyncio

import sqlalchemy as sa

from app.agents.services.agent_service import AgentWorkflowService
from app.ai.services.llm import LLMService
from app.database.base import get_session_factory
from app.database.models import (
    AgentRun,
    AgentRunStatus,
    Conversation,
    ConversationStatus,
    EvalExample,
    EvalRun,
    Message,
    MessageRole,
)
from app.knowledge.rag_service import RAGService


async def run():
    SessionFactory = get_session_factory()
    async with SessionFactory() as db:
        eval_run = await db.scalar(sa.select(EvalRun).order_by(EvalRun.created_at.desc()).limit(1))
        if not eval_run:
            return
        examples = await db.scalars(
            sa.select(EvalExample).where(EvalExample.dataset_id == eval_run.dataset_id)
        )
        examples = examples.all()
        from app.database.models import User

        user = await db.scalar(sa.select(User).limit(1))
        llm = LLMService()
        rag = RAGService(db, llm)
        agent_service = AgentWorkflowService(db, llm, rag)
        for ex in examples:
            print(f"Processing example {ex.id}")
            conv = Conversation(
                organization_id=eval_run.organization_id,
                user_id=user.id,
                title="Eval",
                status=ConversationStatus.ACTIVE,
            )
            db.add(conv)
            await db.flush()
            agent_run = AgentRun(
                conversation_id=conv.id, user_id=user.id, status=AgentRunStatus.PENDING
            )
            db.add(agent_run)
            await db.flush()
            msg = Message(
                conversation_id=conv.id,
                role=MessageRole.USER,
                content=ex.input_prompt,
                agent_run_id=agent_run.id,
            )
            db.add(msg)
            await db.commit()
            print("Executing...")
            state = await agent_service.execute_run(agent_run.id)
            print("Done!", state)
            break


asyncio.run(run())
