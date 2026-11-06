from __future__ import annotations

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database.base import get_db_session
from app.database.models import (
    AgentRun,
    EvalDataset,
    EvalExample,
    EvalResult,
    EvalRun,
    Organization,
    User,
)


@pytest.mark.asyncio
async def test_run_lifecycle_persists_failures_and_continues_without_cloud_llm(
    app, postgres_engine, create_tables, monkeypatch
):
    factory = async_sessionmaker(bind=postgres_engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr("app.database.base.get_session_factory", lambda: factory)

    async def use_test_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = use_test_session
    org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    async with factory() as db:
        await db.merge(Organization(id=org_id, name="Test", slug="eval-test", settings={}))
        await db.merge(
            User(
                id=user_id,
                organization_id=org_id,
                email="eval@example.test",
                full_name="Eval Test",
                is_active=True,
                metadata_={},
            )
        )
        await db.flush()
        dataset = EvalDataset(
            organization_id=org_id, name="Lifecycle test", category="test", version=1
        )
        db.add(dataset)
        await db.flush()
        db.add_all(
            [
                EvalExample(
                    dataset_id=dataset.id,
                    input_prompt="failure",
                    expected_tools=[],
                    expected_output_contains=[],
                    must_not_contain=[],
                    is_attack=False,
                ),
                EvalExample(
                    dataset_id=dataset.id,
                    input_prompt="success",
                    expected_tools=[],
                    expected_output_contains=[],
                    must_not_contain=[],
                    is_attack=False,
                ),
            ]
        )
        await db.commit()
        dataset_id = dataset.id

    started = asyncio.Event()
    release = asyncio.Event()

    class NoCloudLLM:
        provider = None

    class DeterministicAgent:
        def __init__(self, session, *_args, **_kwargs):
            self.session = session

        async def execute_run(self, run_id):
            agent_run = await self.session.get(AgentRun, run_id)
            if agent_run.user_request == "failure":
                started.set()
                await release.wait()
                raise RuntimeError("deterministic test failure")
            agent_run.final_response = "deterministic success"
            await self.session.commit()

    monkeypatch.setattr("app.ai.services.llm.LLMService", NoCloudLLM)
    monkeypatch.setattr(
        "app.agents.services.agent_service.AgentWorkflowService", DeterministicAgent
    )

    from jose import jwt

    token = jwt.encode(
        {"sub": str(user_id), "org_id": str(org_id), "exp": 9999999999, "iss": "aura", "aud": "aura"},
        "test-secret-key-at-least-32-characters-long",
        algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", headers=headers
    ) as client:
        settings = await client.get("/api/v1/settings")
        assert settings.status_code == 200
        settings_payload = settings.json()
        assert settings_payload["organization"]["id"] == str(org_id)
        assert "secret" not in str(settings_payload).lower()

        request_task = asyncio.create_task(
            client.post(
                "/api/v1/eval/runs",
                json={"dataset_id": str(dataset_id), "provider": "mock", "model": "test"},
            )
        )
        await asyncio.wait_for(started.wait(), timeout=5)
        run_list = await client.get("/api/v1/eval/runs")
        assert run_list.status_code == 200
        run_id = run_list.json()["runs"][0]["id"]
        active = await client.get("/api/v1/eval/runs/" + run_id)
        assert active.json()["run"]["status"] == "running"
        release.set()
        response = await request_task
        assert response.status_code == 200
        assert response.json()["status"] == "pending"
        details = await client.get("/api/v1/eval/runs/" + run_id)
        assert details.status_code == 200
        payload = details.json()
        assert payload["run"]["status"] == "completed"
        assert payload["run"]["sample_count"] == 2
        assert len(payload["results"]) == 2
        failures = [result for result in payload["results"] if not result["passed"]]
        passes = [result for result in payload["results"] if result["passed"]]
        assert len(failures) == len(passes) == 1
        assert "deterministic test failure" in failures[0]["error_message"]
        assert passes[0]["actual_output"] == "deterministic success"

    async with factory() as db:
        stored_run = await db.scalar(select(EvalRun).where(EvalRun.id == uuid.UUID(run_id)))
        stored_results = list(
            (
                await db.scalars(select(EvalResult).where(EvalResult.run_id == uuid.UUID(run_id)))
            ).all()
        )
        assert stored_run is not None and stored_run.status == "completed"
        assert len(stored_results) == 2
