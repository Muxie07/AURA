path = "backend/app/ai/providers/heuristic.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text += """
    async def stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        text = (await self.generate(request)).text
        words = text.split(" ")
        for word in words:
            yield word + " "
            import asyncio
            await asyncio.sleep(0.01)

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        return [[0.5] * 1536 for _ in texts]
"""
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed heuristic methods")
