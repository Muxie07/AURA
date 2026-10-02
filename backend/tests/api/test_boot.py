import os
import pytest
from app.main import create_app
from fastapi.testclient import TestClient

def test_app_boots_with_env_example():
    import dotenv
    env_vars = dotenv.dotenv_values("../.env.example")
    # Clean up empty strings or invalid stuff for test if necessary
    os.environ.update({k: str(v) for k, v in env_vars.items() if v is not None})
    os.environ['POSTGRES_PASSWORD'] = 'aura'
    
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200

