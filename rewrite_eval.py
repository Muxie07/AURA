import os

path = "backend/app/api/v1/eval.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Replace the imports and add DatabaseDep
text = text.replace("from app.api.deps import CurrentUserDep", "from app.api.deps import CurrentUserDep, DatabaseDep\nfrom sqlalchemy import select, func\nfrom app.database.models import EvalDataset, EvalExample, EvalRun, EvalResult")

# Replace get_benchmarks
new_benchmarks = """
@router.get("/benchmarks")
async def get_benchmarks(current_user: CurrentUserDep, db: DatabaseDep, task_type: str | None = None) -> dict[str, Any]:
    # Query actual eval runs
    query = select(EvalRun).where(EvalRun.organization_id == current_user.organization_id)
    result = await db.execute(query)
    runs = result.scalars().all()
    
    benchmarks = []
    for r in runs:
        benchmarks.append({
            "model": r.model,
            "provider": r.provider,
            "task_type": "GENERAL",
            "success_rate": r.success_rate,
            "avg_latency_ms": r.avg_latency_ms,
            "avg_tokens": r.avg_tokens,
            "avg_cost_usd": r.avg_cost_usd,
            "sample_count": r.sample_count,
        })
        
    return {
        "benchmarks": benchmarks,
        "recommendation": None
    }
"""

# Find and replace get_benchmarks
import re
text = re.sub(r"@router\.get\(\"/benchmarks\"\).*?return \{.*?\}", new_benchmarks.strip(), text, flags=re.DOTALL)


# Replace get_datasets
new_datasets = """
@router.get("/datasets")
async def get_datasets(current_user: CurrentUserDep, db: DatabaseDep, category: str | None = None) -> dict[str, Any]:
    query = select(EvalDataset).where(EvalDataset.organization_id == current_user.organization_id)
    if category:
        query = query.where(EvalDataset.category == category)
    
    result = await db.execute(query)
    datasets = result.scalars().all()
    
    if not datasets:
        # Seed lazily from ALL_GOLDEN_EXAMPLES
        from app.evaluation.datasets import ALL_GOLDEN_EXAMPLES
        grouped = {}
        for ex in ALL_GOLDEN_EXAMPLES:
            if ex.category not in grouped:
                grouped[ex.category] = []
            grouped[ex.category].append(ex)
            
        for cat, examples in grouped.items():
            ds = EvalDataset(
                organization_id=current_user.organization_id,
                name=f"{cat.title()} Golden Dataset",
                description=f"Standard golden examples for {cat} tasks.",
                category=cat,
                version=1
            )
            db.add(ds)
            await db.flush()
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
                db.add(db_ex)
        await db.commit()
        
        result = await db.execute(query)
        datasets = result.scalars().all()
        
    ds_list = []
    for ds in datasets:
        ds_list.append({
            "id": str(ds.id),
            "name": ds.name,
            "description": ds.description,
            "category": ds.category,
            "version": ds.version
        })
        
    return {
        "count": len(ds_list),
        "examples": ds_list,
        "attacks": 0
    }
"""
text = re.sub(r"@router\.get\(\"/datasets\"\).*?return \{.*?\}", new_datasets.strip(), text, flags=re.DOTALL)


with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("eval.py rewritten")
