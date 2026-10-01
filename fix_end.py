path = "backend/app/ai/providers/heuristic.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Replace the incorrect stream and embed from previous step with the proper suffix
text = text.replace("""    async def stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        text = (await self.generate(request)).text
        words = text.split(" ")
        for word in words:
            yield word + " "
            import asyncio
            await asyncio.sleep(0.01)

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        return [[0.5] * 1536 for _ in texts]
""", """        else:
            from app.ai.errors.exceptions import LLMValidationError
            raise LLMValidationError(f"HeuristicProvider does not support schema {schema.__name__}")

        try:
            parsed = schema.model_validate(data)
        except Exception as e:
            from app.ai.errors.exceptions import LLMValidationError
            raise LLMValidationError(f"HeuristicProvider failed to validate generated data: {e}")
            
        import json
        from app.ai.providers.base import Usage

        result = GenerationResult(
            text=json.dumps(data),
            structured_data=data,
            model=request.model,
            provider=self.name,
            usage=Usage(prompt_tokens=50, completion_tokens=20, total_tokens=70),
            finish_reason="stop",
            raw_response={"heuristic": True}
        )
        return result, parsed

    async def stream(self, request: GenerationRequest):
        text = (await self.generate(request)).text
        words = text.split(" ")
        for word in words:
            yield word + " "
            import asyncio
            await asyncio.sleep(0.01)

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        return [[0.5] * 1536 for _ in texts]
""")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed missing return")
