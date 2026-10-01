path = "backend/app/api/v1/router.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("from app.api.v1.settings import router as settings_router", "from app.api.v1.settings import router as settings_router\nfrom app.api.v1.forecasting import router as forecasting_router")
text = text.replace("api_v1_router.include_router(settings_router)", "api_v1_router.include_router(settings_router)\napi_v1_router.include_router(forecasting_router)")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
