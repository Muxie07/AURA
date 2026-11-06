from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.core.nodes import BaseNode
from app.agents.core.state import AgentNodeState, AgentState
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
        # Domain knowledge keywords that warrant searching the enterprise knowledge base
        req_lower = state.original_request.lower().strip()
        KNOWLEDGE_KEYWORDS = [
            "cloud infotech", "dinstar", "price list", "pricelist", "rate card",
            "catalog", "hardware", "gateway", "fxs", "fxo", "gsm", "volte",
            "ip pbx", "ippbx", "sbc", "session border", "transcoding",
            "quotation", "quote", "invoice", "bill", "billing",
            "warranty", "freight", "dispatch", "payment terms", "credit period",
            "sla", "p1", "incident", "runbook", "latency", "observability",
            "procedure", "support policy"
        ]

        from app.ai.knowledge.adaptive_engine import AdaptiveEngine
        # If the request matches general adaptive engine OR is not a domain knowledge query,
        # skip RAG retrieval completely to avoid polluting context with irrelevant document chunks.
        if (
            AdaptiveEngine.evaluate(state.original_request) is not None
            or not any(kw in req_lower for kw in KNOWLEDGE_KEYWORDS)
        ):
            state.status = AgentNodeState.UNDERSTANDING
            return state

        try:
            rag_response = await self.rag.query(
                organization_id=state.organization_id,
                knowledge_base_id=None,
                question=state.original_request,
            )

            if rag_response.sources:
                state.retrieved_context = [
                    {
                        "source": s.source,
                        "content": s.content,
                        "chunk_id": s.chunk_id,
                        "score": s.score,
                        "metadata": s.metadata,
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
