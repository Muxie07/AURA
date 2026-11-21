import os
import asyncio
from dotenv import load_dotenv

from pydantic import BaseModel
from backend.app.ai.providers.google import GeminiProvider
from backend.app.ai.schemas.generation import GenerationRequest, Message

# Ensure env vars are loaded
load_dotenv()

class MySchema(BaseModel):
    status: str
    message: str

async def main():
    try:
        provider = GeminiProvider()
    except Exception as e:
        print(f"Provider initialization failed: {e}")
        return

    print(f"Testing {provider.name} provider...")

    # 1. Test standard generation
    req = GenerationRequest(
        model="gemini-1.5-flash",
        messages=[Message(role="user", content="Say 'Hello, World!'")],
        temperature=0.0
    )
    
    try:
        print("Testing generate()...")
        res = await provider.generate(req)
        print(f"Generate Success: {res.text.strip()}")
    except Exception as e:
        print(f"Generate Failed: {type(e).__name__} - {e}")
        if "quota" in str(e).lower() or "429" in str(e):
            print("Quota unavailable or rate limit exceeded.")

    # 2. Test structured generation
    try:
        print("\nTesting generate_structured()...")
        res, structured_res = await provider.generate_structured(req, MySchema)
        print(f"Structured Generation Success: status={structured_res.status}, message={structured_res.message}")
    except Exception as e:
        print(f"Structured Generate Failed: {type(e).__name__} - {e}")
        if "quota" in str(e).lower() or "429" in str(e):
            print("Quota unavailable or rate limit exceeded.")

    # 3. Test retry / error handling (simulate invalid model)
    req_bad = GenerationRequest(
        model="invalid-model-name",
        messages=[Message(role="user", content="Hello")],
    )
    try:
        print("\nTesting error handling with invalid model...")
        await provider.generate(req_bad)
    except Exception as e:
        print(f"Error handling verified. Caught exception: {type(e).__name__} - {e}")

if __name__ == "__main__":
    asyncio.run(main())
