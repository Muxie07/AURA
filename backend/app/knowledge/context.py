from app.knowledge.retrieval import RetrievalResult


class ContextBuilder:
    """Builds context prompts from retrieved chunks."""

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens

    def build_context(self, results: list[RetrievalResult]) -> str:
        """
        Deduplicates, orders, and formats the retrieved chunks into a context string.
        Includes citations.
        """
        # Simple deduplication by chunk_id
        seen = set()
        unique_results = []
        for r in results:
            if r.chunk_id not in seen:
                seen.add(r.chunk_id)
                unique_results.append(r)

        # Format
        context_parts = []
        approx_tokens = 0

        for idx, r in enumerate(unique_results, 1):
            page_info = f"<page>{r.metadata['approx_page']}</page>\n" if "approx_page" in r.metadata else ""

            chunk_str = (
                f"<document index=\"{idx}\">\n"
                f"<source>{r.source}</source>\n"
                f"<chunk_id>{r.chunk_id}</chunk_id>\n"
                f"{page_info}"
                f"<content>\n{r.content}\n</content>\n"
                f"</document>\n"
            )

            # Very rough token approximation (4 chars = 1 token)
            chunk_tokens = len(chunk_str) // 4
            if approx_tokens + chunk_tokens > self.max_tokens:
                break

            context_parts.append(chunk_str)
            approx_tokens += chunk_tokens

        return "\n".join(context_parts)
