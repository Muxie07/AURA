import asyncio
import uuid
import sys
from app.database.base import get_session_factory, initialize_database
from app.api.v1.runs import run_agent_in_background
from app.config.settings import get_settings

async def main():
    await initialize_database()
    run_id = sys.argv[1]
    print(f"Executing run {run_id}...")
    await run_agent_in_background(uuid.UUID(run_id))
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
