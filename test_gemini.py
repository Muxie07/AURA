import asyncio
from app.ai.providers.google import GeminiProvider
from app.ai.schemas.generation import GenerationRequest, Message

async def main():
    try:
        provider = GeminiProvider()
        req = GenerationRequest(
            model="gemini-2.5-flash",
            messages=[Message(role="user", content="Say 'AURA Phase 9 Live Test SUCCESS'")]
        )
        res = await provider.generate(req)
        print("GEMINI_RESPONSE:", res.text)
    except Exception as e:
        print("GEMINI_ERROR:", str(e))

asyncio.run(main())
