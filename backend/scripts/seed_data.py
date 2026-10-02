import asyncio
import os
import sys
import uuid

import bcrypt
from sqlalchemy import select

from app.config.settings import get_settings
from app.database.base import get_session_factory
from app.database.models import (
    AgentRun,
    AgentRunStatus,
    Customer,
    Organization,
    User,
)

settings = get_settings()

if settings.aura_env.value != "development":
    print("Refusing to seed in non-development environment.")
    sys.exit(1)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

async def seed_data():
    SessionFactory = get_session_factory()
    demo_pass = os.environ.get("AURA_DEMO_PASSWORD", "demo1234")
    hashed_pass = hash_password(demo_pass)

    async with SessionFactory() as db:
        # Create Main Org
        stmt = select(Organization).where(Organization.slug == "aura-sre")
        org = (await db.execute(stmt)).scalars().first()
        if not org:
            org = Organization(id=uuid.uuid4(), name="AURA SRE", slug="aura-sre", is_active=True, settings={})
            db.add(org)
            await db.flush()

        # Create Evil Org (Tenant Isolation testing)
        stmt2 = select(Organization).where(Organization.slug == "evil-corp")
        org2 = (await db.execute(stmt2)).scalars().first()
        if not org2:
            org2 = Organization(id=uuid.uuid4(), name="Evil Corp", slug="evil-corp", is_active=True, settings={})
            db.add(org2)
            await db.flush()

        # Create roles for Main Org
        roles = [
            ("admin@aura-sre.com", "Admin User", True),
            ("demo@aura-sre.com", "Demo User", False),
        ]

        main_user = None
        for email, name, is_super in roles:
            ustmt = select(User).where(User.email == email)
            u = (await db.execute(ustmt)).scalars().first()
            if not u:
                u = User(
                    id=uuid.uuid4(), organization_id=org.id, email=email,
                    full_name=name, is_active=True, is_superuser=is_super, metadata_={},
                    hashed_password=hashed_pass
                )
                db.add(u)
            else:
                u.hashed_password = hashed_pass
            if email == "demo@aura-sre.com":
                main_user = u

        await db.flush()

        # Customers
        cstmt = select(Customer).where(Customer.organization_id == org.id)
        existing_c = (await db.execute(cstmt)).scalars().first()
        if not existing_c:
            for i in range(5):
                c = Customer(
                    id=uuid.uuid4(), organization_id=org.id, name=f"Customer {i}",
                    email=f"cust{i}@example.com", status="active",
                    tier="enterprise", tags=["demo"]
                )
                db.add(c)

        # Runs and Approvals
        if main_user:
            rstmt = select(AgentRun).where(AgentRun.organization_id == org.id)
            existing_r = (await db.execute(rstmt)).scalars().first()
            if not existing_r:
                for i in range(15):
                    run = AgentRun(
                        id=uuid.uuid4(), organization_id=org.id, user_id=main_user.id,
                        conversation_id=uuid.uuid4(), user_request=f"Request {i}",
                        status=AgentRunStatus.COMPLETED
                    )
                    db.add(run)

        await db.commit()
        print("Seed complete.")

if __name__ == "__main__":
    asyncio.run(seed_data())
