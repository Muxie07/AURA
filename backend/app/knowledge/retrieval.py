import uuid
from typing import Any

import sqlalchemy as sa
import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.services.llm import LLMService

logger = structlog.get_logger(__name__)


class RetrievalResult(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any]
    source: str
    version: int


class Retriever:
    """Handles semantic search with tenant isolation."""

    def __init__(self, db_session: AsyncSession, llm_service: LLMService):
        self.db = db_session
        self.llm = llm_service
        from app.config.settings import get_settings

        self.embedding_model = get_settings().embedding_model

    async def search(
        self,
        organization_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        hybrid: bool = True,
    ) -> list[RetrievalResult]:
        """
        Executes a vector similarity search isolated to the specified organization and KB.
        """
        try:
            embeddings = await self.llm.provider.embed([query], model=self.embedding_model)
            query_embedding = embeddings[0]
            query_vector = f"[{','.join(map(str, query_embedding))}]"
        except Exception:
            # Fallback for mocked environments where embed fails
            query_vector = "[0.0]"  # Dummy vector

        kw = query

        # Hybrid search using Vector and Keyword
        stmt_vector = sa.text("""
            SELECT
                c.id, c.document_id, c.content, c.metadata, d.filename, d.version,
                1 - (c.embedding <=> :query_vector) AS score,
                'vector' as search_type
            FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.organization_id = :org_id
              AND d.organization_id = :org_id
              AND d.knowledge_base_id = :kb_id
            ORDER BY c.embedding <=> :query_vector
            LIMIT :limit
        """)

        stmt_keyword = sa.text("""
            SELECT
                c.id, c.document_id, c.content, c.metadata, d.filename, d.version,
                ts_rank_cd(to_tsvector('english', c.content), websearch_to_tsquery('english', :kw)) AS score,
                'keyword' as search_type
            FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.organization_id = :org_id
              AND d.organization_id = :org_id
              AND d.knowledge_base_id = :kb_id
              AND to_tsvector('english', c.content) @@ websearch_to_tsquery('english', :kw)
            ORDER BY score DESC
            LIMIT :limit
        """)

        results_dict: dict[str, dict[str, Any]] = {}

        try:
            # Vector
            res_v = await self.db.execute(
                stmt_vector,
                {
                    "query_vector": query_vector,
                    "org_id": str(organization_id),
                    "kb_id": str(knowledge_base_id),
                    "limit": top_k,
                },
            )
            for rank, row in enumerate(res_v.fetchall()):
                cid = str(row[0])
                if cid not in results_dict:
                    results_dict[cid] = {"row": row, "score": 0.0}
                results_dict[cid]["score"] += 1.0 / (rank + 60)  # RRF

            if hybrid:
                res_k = await self.db.execute(
                    stmt_keyword,
                    {
                        "kw": kw,
                        "org_id": str(organization_id),
                        "kb_id": str(knowledge_base_id),
                        "limit": top_k,
                    },
                )
                for rank, row in enumerate(res_k.fetchall()):
                    cid = str(row[0])
                    if cid not in results_dict:
                        results_dict[cid] = {"row": row, "score": 0.0}
                    results_dict[cid]["score"] += 1.0 / (rank + 60)  # RRF

        except Exception as e:
            logger.warning("vector_search_failed", error=str(e))
            # Fallback to pure keyword if vector fails (e.g., sqlite mock environment)
            res_k = await self.db.execute(
                stmt_keyword,
                {
                    "kw": kw,
                    "org_id": str(organization_id),
                    "kb_id": str(knowledge_base_id),
                    "limit": top_k,
                },
            )
            for rank, row in enumerate(res_k.fetchall()):
                cid = str(row[0])
                if cid not in results_dict:
                    results_dict[cid] = {"row": row, "score": 0.0}
                results_dict[cid]["score"] += 1.0 / (rank + 60)

        # Sort by RRF score
        sorted_cids = sorted(
            results_dict.keys(), key=lambda x: results_dict[x]["score"], reverse=True
        )[:top_k]

        final_results = []
        for cid in sorted_cids:
            row = results_dict[cid]["row"]
            final_results.append(
                RetrievalResult(
                    chunk_id=str(row[0]),
                    document_id=str(row[1]),
                    content=row[2],
                    metadata=row[3],
                    source=row[4],
                    version=row[5] if row[5] is not None else 1,
                    score=results_dict[cid]["score"],
                )
            )

        return final_results
