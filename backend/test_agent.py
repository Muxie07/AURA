import asyncio
import sys
import uuid

from app.api.v1.runs import run_agent_in_background
from app.database.base import initialize_database


async def main():
    await initialize_database()
    run_id = sys.argv[1]
    print(f"Executing run {run_id}...")
    await run_agent_in_background(uuid.UUID(run_id))
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
