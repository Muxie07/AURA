import uuid
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import CurrentUserDep, DatabaseDep
from app.database.models import ExternalToolEndpoint, IntegrationCredential
from app.security.vault import CredentialVault
from app.tools.builtin import register_builtin_tools
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolContext
from app.tools.utcp.manager import UTCPClientManager

router = APIRouter(prefix="/tools", tags=["tools"])

# Global shared registry reference
_tools_registry = ToolRegistry()
register_builtin_tools(_tools_registry)


class RegisterUTCPRequest(BaseModel):
    name: str = Field(description="Display name for this UTCP tool integration")
    base_url: str = Field(description="Base URL of the external tool service")
    manifest_url: str | None = None
    manifest_data: dict[str, Any] | None = None
    credential_token: str | None = None
    credential_type: str = Field(default="bearer")  # 'bearer', 'api_key', 'header'
    header_name: str | None = "X-API-Key"


class TestUTCPRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


@router.get("", summary="List all tools across Internal, MCP, and UTCP")
async def list_tools(current_user: CurrentUserDep, db: DatabaseDep) -> dict[str, Any]:
    # Sync active UTCP endpoints for this tenant
    try:
        stmt = sa.select(ExternalToolEndpoint).where(
            ExternalToolEndpoint.organization_id == current_user.organization_id,
            ExternalToolEndpoint.is_active == True,
        )
        endpoints = (await db.scalars(stmt)).all()
        manager = UTCPClientManager(_tools_registry)
        for ep in endpoints:
            if ep.manifest_data:
                await manager.register_manifest(
                    current_user.organization_id, ep.manifest_data, registry=_tools_registry
                )
    except Exception:
        pass

    definitions = _tools_registry.list_definitions()
    return {
        "tools": [
            {
                "name": d.name,
                "version": d.version,
                "description": d.description,
                "source": d.source.value,
                "risk_level": d.risk_level.value,
                "requires_approval": d.requires_approval,
                "idempotent": d.idempotent,
                "timeout_seconds": d.timeout_seconds,
                "input_schema": d.input_schema,
            }
            for d in definitions
        ]
    }


@router.get("/utcp", summary="List registered UTCP endpoints")
async def list_utcp_endpoints(current_user: CurrentUserDep, db: DatabaseDep) -> dict[str, Any]:
    stmt = sa.select(ExternalToolEndpoint).where(
        ExternalToolEndpoint.organization_id == current_user.organization_id,
        ExternalToolEndpoint.protocol == "utcp",
    )
    endpoints = (await db.scalars(stmt)).all()
    return {
        "endpoints": [
            {
                "id": str(ep.id),
                "name": ep.name,
                "protocol": ep.protocol,
                "base_url": ep.base_url,
                "manifest_url": ep.manifest_url,
                "is_active": ep.is_active,
                "health_status": ep.health_status,
                "has_credential": ep.credential_id is not None,
                "created_at": ep.created_at.isoformat() if ep.created_at else None,
            }
            for ep in endpoints
        ]
    }


@router.post("/utcp", summary="Register a new UTCP endpoint/manifest")
async def register_utcp_endpoint(
    req: RegisterUTCPRequest, current_user: CurrentUserDep, db: DatabaseDep
) -> dict[str, Any]:
    org_id = current_user.organization_id

    # 1. Store encrypted credential if provided
    credential_id = None
    if req.credential_token:
        encrypted = CredentialVault.encrypt_secret(req.credential_token, org_id)
        cred = IntegrationCredential(
            id=uuid.uuid4(),
            organization_id=org_id,
            name=f"{req.name}-credential",
            credential_type=req.credential_type,
            encrypted_payload=encrypted,
            header_name=req.header_name,
        )
        db.add(cred)
        await db.flush()
        credential_id = cred.id

    # 2. Parse & validate manifest
    manifest_data = req.manifest_data or {
        "utcp_version": "1.0.0",
        "name": req.name,
        "base_url": req.base_url,
        "tools": [],
    }

    endpoint = ExternalToolEndpoint(
        id=uuid.uuid4(),
        organization_id=org_id,
        protocol="utcp",
        name=req.name,
        base_url=req.base_url,
        manifest_url=req.manifest_url,
        manifest_data=manifest_data,
        credential_id=credential_id,
        is_active=True,
        health_status="active",
    )
    db.add(endpoint)
    await db.commit()

    # 3. Synchronize with memory registry
    manager = UTCPClientManager(_tools_registry)
    if req.manifest_data:
        await manager.register_manifest(org_id, req.manifest_data, registry=_tools_registry)

    return {
        "status": "registered",
        "endpoint_id": str(endpoint.id),
        "name": endpoint.name,
        "protocol": "utcp",
    }


@router.post("/utcp/test", summary="Test or simulate a UTCP tool execution")
async def test_utcp_tool(
    req: TestUTCPRequest, current_user: CurrentUserDep, db: DatabaseDep
) -> dict[str, Any]:
    if req.tool_name not in _tools_registry._tools:
        raise HTTPException(status_code=404, detail=f"Tool '{req.tool_name}' not found.")

    context = ToolContext(
        organization_id=current_user.organization_id,
        execution_id=uuid.uuid4().hex,
        dry_run=req.dry_run,
        user_id=current_user.id,
    )

    result = await _tools_registry.execute(db, req.tool_name, req.arguments, context)
    return {
        "status": result.status,
        "result": result.result,
        "message": result.message,
        "error_type": result.error_type,
        "retryable": result.retryable,
    }
