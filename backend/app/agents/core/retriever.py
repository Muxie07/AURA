from typing import Any

import sqlalchemy as sa
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.core.nodes import BaseNode
from app.agents.core.state import AgentNodeState, AgentState
from app.database.models import KnowledgeBase
from app.knowledge.rag_service import RAGService

logger = structlog.get_logger(__name__)

class RetrieveNode(BaseNode):
    def __init__(self, db: AsyncSession, rag_service: RAGService):
        self.db = db
        self.rag = rag_service

    @property
    def name(self) -> str:
        return "RetrieveNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        # In a sophisticated system, this node would decide *whether* to retrieve.
        # For Phase 4, we conditionally query the KB if the plan dictates or context implies.
        # Here we do a broad retrieval based on the original request to enrich context.

        try:
            # Get the first KB for the org
            result = await self.db.execute(
                sa.select(KnowledgeBase).where(KnowledgeBase.organization_id == state.organization_id)
            )
            kb = result.scalars().first()

            if kb:
                rag_response = await self.rag.query(
                    organization_id=state.organization_id,
                    knowledge_base_id=kb.id,
                    question=state.original_request
                )

                if rag_response.sources:
                    state.retrieved_context = [
                        {
                            "source": s.source,
                            "content": s.content,
                            "chunk_id": s.chunk_id,
                            "score": s.score,
                            "metadata": s.metadata
                        }
                        for s in rag_response.sources
                    ]

            # Transition to DECISION phase
            state.status = AgentNodeState.UNDERSTANDING

        except Exception as e:
            logger.error("retrieval_node_failed", error=str(e), run_id=str(state.run_id))
            # Retrieval failure is non-fatal usually, we just proceed
            state.status = AgentNodeState.UNDERSTANDING

        return state
