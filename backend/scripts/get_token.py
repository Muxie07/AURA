import asyncio
import os
import sys
from datetime import datetime, timedelta

from jose import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy import select

from app.config.settings import get_settings
from app.database.base import get_session_factory, initialize_database
from app.database.models import User


async def main():
    settings = get_settings()
    await initialize_database()
    async with get_session_factory()() as session:
        result = await session.execute(select(User))
        user = result.scalars().first()
        if not user:
            print("No users found")
            return

        payload = {
            "sub": str(user.id),
            "org_id": str(user.organization_id),
            "exp": datetime.utcnow() + timedelta(days=1),
        }
        token = jwt.encode(payload, settings.aura_secret_key.get_secret_value(), algorithm="HS256")
        print(token)


if __name__ == "__main__":
    asyncio.run(main())
