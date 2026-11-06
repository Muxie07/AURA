import os

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_app_boots_with_env_example(monkeypatch):
    import dotenv
    env_vars = dotenv.dotenv_values("../.env.example")
    # Clean up empty strings or invalid stuff for test if necessary
    for k, v in env_vars.items():
        if v is not None:
            monkeypatch.setenv(k, str(v))
    monkeypatch.setenv('POSTGRES_PASSWORD', 'aura')

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
