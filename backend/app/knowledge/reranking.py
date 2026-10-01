from abc import ABC, abstractmethod

import httpx

from app.knowledge.retrieval import RetrievalResult


class Reranker(ABC):
    """Abstract interface for reranking candidate results."""

    @abstractmethod
    async def rerank(self, query: str, candidates: list[RetrievalResult]) -> list[RetrievalResult]:
        """Reranks the candidates based on relevance to the query."""
        pass


class FallbackReranker(Reranker):
    """
    Deterministic fallback reranker (identity pass-through).
    """

    async def rerank(self, query: str, candidates: list[RetrievalResult]) -> list[RetrievalResult]:
        _ = query
        return sorted(candidates, key=lambda x: x.score, reverse=True)


class CohereReranker(Reranker):
    """
    Production reranker using Cohere API.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def rerank(self, query: str, candidates: list[RetrievalResult]) -> list[RetrievalResult]:
        if not candidates:
            return []
        try:
            docs = [c.content for c in candidates]
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.cohere.ai/v1/rerank",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"query": query, "documents": docs, "model": "rerank-english-v3.0"},
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])

                reranked = []
                for r in results:
                    idx = r["index"]
                    score = r["relevance_score"]
                    candidate = candidates[idx]
                    candidate.score = float(score)
                    reranked.append(candidate)
                return reranked
        except Exception:
            return sorted(candidates, key=lambda x: x.score, reverse=True)
