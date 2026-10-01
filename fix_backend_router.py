path = "backend/app/api/v1/router.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('api_v1_router.include_router(runs_router)', 'api_v1_router.include_router(runs_router, prefix="/agent", tags=["agent"])')

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Updated backend router")
