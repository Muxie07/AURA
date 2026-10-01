#!/usr/bin/env python3
"""
AURA — Seed Data Script.

Populates the database with realistic demo data for local development:
- Demo organization
- Demo users
- Sample conversations
- Sample messages

Run this after `alembic upgrade head`.

Usage:
    python scripts/seed_data.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import os

os.chdir(Path(__file__).parent.parent / "backend")

from app.config.settings import get_settings
from app.database.models import (
    Conversation,
    ConversationStatus,
    Message,
    MessageRole,
    Organization,
    User,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

settings = get_settings()

# Fixed IDs for reproducible seeding
ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
MANAGER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")


async def seed_organization(session: AsyncSession) -> Organization:
    """Create the demo organization if it doesn't exist."""
    result = await session.execute(
        select(Organization).where(Organization.id == ORG_ID)
    )
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  [skip] Organization already exists: {existing.name}")
        return existing

    org = Organization(
        id=ORG_ID,
        name="Acme Corporation",
        slug="acme-corp",
        is_active=True,
        settings={
            "tier": "enterprise",
            "max_agent_runs_per_day": 1000,
            "features": ["quotation", "crm", "email"],
        },
    )
    session.add(org)
    await session.flush()
    print(f"  [created] Organization: {org.name}")
    return org


async def seed_users(session: AsyncSession, org: Organization) -> tuple[User, User]:
    """Create demo users."""
    # Admin user
    result = await session.execute(select(User).where(User.id == USER_ID))
    admin = result.scalar_one_or_none()
    if not admin:
        admin = User(
            id=USER_ID,
            organization_id=org.id,
            email="admin@acme.example.com",
            full_name="Alice Admin",
            is_active=True,
            is_superuser=True,
            metadata_={"role": "admin", "department": "Operations"},
        )
        session.add(admin)
        print(f"  [created] User: {admin.email}")
    else:
        print(f"  [skip] User already exists: {admin.email}")

    # Manager user
    result2 = await session.execute(select(User).where(User.id == MANAGER_ID))
    manager = result2.scalar_one_or_none()
    if not manager:
        manager = User(
            id=MANAGER_ID,
            organization_id=org.id,
            email="manager@acme.example.com",
            full_name="Bob Manager",
            is_active=True,
            is_superuser=False,
            metadata_={"role": "sales_manager", "department": "Sales"},
        )
        session.add(manager)
        print(f"  [created] User: {manager.email}")
    else:
        print(f"  [skip] User already exists: {manager.email}")

    await session.flush()
    return admin, manager


async def seed_conversations(
    session: AsyncSession, org: Organization, user: User
) -> None:
    """Create sample conversations with realistic messages."""
    # Check if we already have conversations
    result = await session.execute(
        select(Conversation).where(Conversation.organization_id == org.id).limit(1)
    )
    if result.scalar_one_or_none():
        print("  [skip] Conversations already seeded.")
        return

    # --- Conversation 1: Quotation request ---
    conv1 = Conversation(
        organization_id=org.id,
        user_id=user.id,
        title="Quotation Request — Product X — Customer ABC",
        status=ConversationStatus.ACTIVE,
        metadata_={"workflow": "quotation", "priority": "high"},
    )
    session.add(conv1)
    await session.flush()

    messages1 = [
        Message(
            conversation_id=conv1.id,
            role=MessageRole.USER,
            content="Hello, we need 500 units of Product X for our Q4 campaign. "
            "Please send us a quotation for Customer ABC (ID: CUST-001).",
        ),
        Message(
            conversation_id=conv1.id,
            role=MessageRole.ASSISTANT,
            content=(
                "I'll prepare a quotation for 500 units of Product X for Customer ABC. "
                "Let me look up the customer details, product pricing, and applicable policies."
            ),
            structured_content={
                "type": "agent_acknowledgement",
                "planned_steps": [
                    "Lookup customer CUST-001",
                    "Lookup Product X details",
                    "Retrieve pricing for volume 500",
                    "Check company discount policies",
                    "Generate quotation draft",
                ],
            },
        ),
    ]
    session.add_all(messages1)

    # --- Conversation 2: Completed ---
    conv2 = Conversation(
        organization_id=org.id,
        user_id=user.id,
        title="Invoice Processing — INV-2024-1234",
        status=ConversationStatus.COMPLETED,
        metadata_={"workflow": "invoice_processing"},
    )
    session.add(conv2)
    await session.flush()

    session.add(
        Message(
            conversation_id=conv2.id,
            role=MessageRole.USER,
            content="Process invoice INV-2024-1234 and update the CRM.",
        )
    )

    await session.flush()
    print("  [created] 2 sample conversations with messages.")


async def main() -> None:
    """Run all seed operations."""
    print("\n🌱 AURA Seed Data")
    print("=" * 40)

    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session, session.begin():
        org = await seed_organization(session)
        admin, manager = await seed_users(session, org)
        await seed_conversations(session, org, admin)

    await engine.dispose()
    print("\n✅ Seed complete!")
    print(f"   Org ID:    {ORG_ID}")
    print(f"   User ID:   {USER_ID}")
    print("   API Docs:  http://localhost:8000/docs")
    print()


if __name__ == "__main__":
    asyncio.run(main())
