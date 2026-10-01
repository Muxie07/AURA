import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ai.providers.google import GeminiProvider

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

async def main():
    try:
        provider = GeminiProvider()
        print("Available models:")
        async for m in provider.client.aio.models.list_models():
            print(m.name)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
