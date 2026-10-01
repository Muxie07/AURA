import re
import os

filepath = r"backend/app/api/v1/eval.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Add current_user: CurrentUserDep to the vulnerable endpoints and the org check
# /safety
content = re.sub(
    r'(async def evaluate_safety\(req: EvaluateSafetyRequest\)) -> SafetyScore:',
    r'\1, current_user: CurrentUserDep) -> SafetyScore:\n    if current_user.organization_id != req.organization_id:\n        raise HTTPException(status_code=403, detail="Access denied")',
    content
)

# /quality
content = re.sub(
    r'(async def evaluate_quality\(req: EvaluateQualityRequest\)) -> QualityScore:',
    r'\1, current_user: CurrentUserDep) -> QualityScore:\n    if current_user.organization_id != req.organization_id:\n        raise HTTPException(status_code=403, detail="Access denied")',
    content
)

# /cost
content = re.sub(
    r'(async def estimate_cost\(req: CostEstimateRequest\)) -> dict\[str, Any\]:',
    r'\1, current_user: CurrentUserDep) -> dict[str, Any]:\n    if current_user.organization_id != req.organization_id:\n        raise HTTPException(status_code=403, detail="Access denied")',
    content
)

# /benchmarks
content = re.sub(
    r'(async def get_benchmarks\(task_type: str \| None = None\)) -> dict\[str, Any\]:',
    r'\1, current_user: CurrentUserDep) -> dict[str, Any]:',
    content
)

# /datasets
content = re.sub(
    r'(async def get_datasets\(category: str \| None = None\)) -> dict\[str, Any\]:',
    r'\1, current_user: CurrentUserDep) -> dict[str, Any]:',
    content
)

# /datasets/evaluate
content = re.sub(
    r'(async def evaluate_against_golden\(req: GoldenEvalRequest\)) -> dict\[str, Any\]:',
    r'\1, current_user: CurrentUserDep) -> dict[str, Any]:',
    content
)

# /incidents
content = re.sub(
    r'(async def log_incident\(req: LogIncidentRequest\)) -> dict\[str, Any\]:',
    r'\1, current_user: CurrentUserDep) -> dict[str, Any]:\n    if current_user.organization_id != req.organization_id:\n        raise HTTPException(status_code=403, detail="Access denied")',
    content
)

# /replay/record
content = re.sub(
    r'(async def record_replay\(req: RecordReplayRequest\)) -> dict\[str, Any\]:',
    r'\1, current_user: CurrentUserDep) -> dict[str, Any]:\n    if current_user.organization_id != req.organization_id:\n        raise HTTPException(status_code=403, detail="Access denied")',
    content
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("eval.py updated successfully")
