with open("backend/app/ai/providers/google.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "async def generate_structured(\n        self, request: GenerationRequest, schema: type[T]\n    ) -> tuple[GenerationResult, T]:\n    async def _old_generate_structured(",
    "async def generate_structured("
)

with open("backend/app/ai/providers/google.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed google.py")
