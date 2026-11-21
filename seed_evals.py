import asyncio
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.database.models import Organization, EvalDataset, EvalExample
from app.evaluation.datasets import ALL_GOLDEN_EXAMPLES

DATABASE_URL = "postgresql+asyncpg://aura:aura-dev-password@aura-postgres:5432/aura"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        result = await session.execute(select(Organization).limit(1))
        org = result.scalar_one_or_none()
        if not org:
            print("No organization found.")
            return

        datasets = {}
        for ex in ALL_GOLDEN_EXAMPLES:
            if ex.category not in datasets:
                datasets[ex.category] = []
            datasets[ex.category].append(ex)

        for cat, examples in datasets.items():
            ds = EvalDataset(
                organization_id=org.id,
                name=f"{cat.title()} Golden Dataset",
                description=f"Standard golden examples for {cat} tasks.",
                category=cat,
                version=1
            )
            session.add(ds)
            await session.flush()
            
            for ex in examples:
                db_ex = EvalExample(
                    dataset_id=ds.id,
                    input_prompt=ex.input,
                    expected_tools=ex.expected_tools,
                    expected_output_contains=ex.expected_output_contains,
                    must_not_contain=ex.must_not_contain,
                    is_attack=ex.is_attack,
                    attack_type=ex.attack_type
                )
                session.add(db_ex)
        
        await session.commit()
        print("Seeded datasets and examples.")

asyncio.run(main())
