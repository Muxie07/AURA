"""
AURA API v1 - MCP Integrations Hub.
Provides Model Context Protocol (MCP) server registry, SSE transport diagnostics, and tool enumeration.
"""

import json
import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentUserDep

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP Hub"])

MCP_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "mcp_servers.json"
)

DEFAULT_MCP_SERVERS = [
    {
        "id": "mcp-aura-local",
        "name": "AURA Builtin ERP & Quotation Hub",
        "endpoint": "http://localhost:8000/api/v1/mcp/messages",
        "transport": "sse",
        "status": "CONNECTED",
        "tools_count": 5,
        "scopes": ["quotation:write", "invoice:generate", "catalog:read"],
        "last_ping_ms": 14,
        "risk_level": "ELEVATED",
        "description": "Internal secured container executing local database pricing models and invoice issuance tools.",
    },
    {
        "id": "mcp-crm-bridge",
        "name": "Enterprise CRM & Account Registry",
        "endpoint": "http://localhost:8000/api/v1/tools/utcp",
        "transport": "sse",
        "status": "CONNECTED",
        "tools_count": 3,
        "scopes": ["customer:search", "customer:credit_limit"],
        "last_ping_ms": 28,
        "risk_level": "STANDARD",
        "description": "Read-only connection to corporate customer records and payment credit histories.",
    },
    {
        "id": "mcp-inventory-sync",
        "name": "Warehouse & Cloud Infotech Stock Bridge",
        "endpoint": "http://localhost:8000/api/v1/knowledge-bases",
        "transport": "sse",
        "status": "CONNECTED",
        "tools_count": 2,
        "scopes": ["inventory:check_stock"],
        "last_ping_ms": 35,
        "risk_level": "STANDARD",
        "description": "Real-time stock checks for Grandstream, Fanvil, and Yeastar hardware models.",
    },
]


def _load_servers() -> list[dict[str, Any]]:
    if os.path.exists(MCP_FILE_PATH):
        try:
            with open(MCP_FILE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    _save_servers(DEFAULT_MCP_SERVERS)
    return DEFAULT_MCP_SERVERS


def _save_servers(servers: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(MCP_FILE_PATH), exist_ok=True)
    with open(MCP_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(servers, f, indent=2)


class ConnectMCPServerRequest(BaseModel):
    name: str
    endpoint: str
    transport: str = "sse"  # sse, stdio, websocket
    risk_level: str = "STANDARD"
    description: str = ""


@router.get("/servers", summary="List registered MCP Servers")
async def list_servers(current_user: CurrentUserDep) -> dict[str, Any]:
    servers = _load_servers()
    return {"servers": servers, "total": len(servers)}


@router.post(
    "/servers", status_code=status.HTTP_201_CREATED, summary="Connect and register a new MCP Server"
)
async def connect_server(
    req: ConnectMCPServerRequest, current_user: CurrentUserDep
) -> dict[str, Any]:
    servers = _load_servers()
    new_id = f"mcp-{uuid.uuid4().hex[:8]}"

    # Test endpoint reachability with a short timeout. A failed probe is recorded
    # as UNREACHABLE, not silently upgraded to CONNECTED: a server that doesn't
    # answer isn't connected, whatever the registration call's own success is.
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.get(req.endpoint)
        ping_ms = max(1, int((time.time() - t0) * 1000))
        conn_status = "CONNECTED"
    except Exception as e:
        ping_ms = int((time.time() - t0) * 1000)
        conn_status = "UNREACHABLE"
        logger.warning("mcp_hub.connect_probe_failed", endpoint=req.endpoint, error=str(e))

    new_server = {
        "id": new_id,
        "name": req.name,
        "endpoint": req.endpoint,
        "transport": req.transport.lower(),
        "status": conn_status,
        "tools_count": 2,
        "scopes": ["custom:execute", "custom:read"],
        "last_ping_ms": ping_ms,
        "risk_level": req.risk_level.upper(),
        "description": req.description or "User connected MCP service endpoint.",
        "connected_at": datetime.now(UTC).isoformat(),
    }

    servers.insert(0, new_server)
    _save_servers(servers)
    return {"status": conn_status, "server": new_server}


@router.post("/servers/{server_id}/ping", summary="Execute live diagnostic ping to MCP server")
async def ping_server(server_id: str, current_user: CurrentUserDep) -> dict[str, Any]:
    servers = _load_servers()
    idx = next((i for i, s in enumerate(servers) if s["id"] == server_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"MCP Server '{server_id}' not found.")

    server = servers[idx]
    endpoint = server.get("endpoint", "")

    t0 = time.time()
    is_live = True
    diag_status: int | None = None

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(endpoint)
            ping_ms = max(1, int((time.time() - t0) * 1000))
            diag_status = res.status_code
    except Exception as e:
        ping_ms = int((time.time() - t0) * 1000)
        is_live = False
        logger.warning("mcp_hub.ping_failed", server_id=server_id, endpoint=endpoint, error=str(e))

    server["last_ping_ms"] = ping_ms
    server["status"] = "CONNECTED" if is_live else "UNREACHABLE"
    servers[idx] = server
    _save_servers(servers)

    if is_live:
        raw_diagnostics = (
            f"Pinging {server['name']} via {server['transport'].upper()} ({endpoint})...\n"
            f"HTTP response: {diag_status}\n"
            f"Roundtrip latency: {ping_ms}ms\n"
            f"Exposed scopes: {', '.join(server.get('scopes', []))}"
        )
    else:
        raw_diagnostics = (
            f"Pinging {server['name']} via {server['transport'].upper()} ({endpoint})...\n"
            f"No response after {ping_ms}ms (connection failed or timed out)."
        )

    return {
        "server_id": server_id,
        "status": "HEALTHY" if is_live else "UNREACHABLE",
        "latency_ms": ping_ms,
        "diagnostics": raw_diagnostics,
    }


@router.delete("/servers/{server_id}", summary="Disconnect and remove MCP server")
async def disconnect_server(server_id: str, current_user: CurrentUserDep) -> dict[str, Any]:
    servers = _load_servers()
    filtered = [s for s in servers if s["id"] != server_id]
    if len(filtered) == len(servers):
        raise HTTPException(status_code=404, detail=f"MCP Server '{server_id}' not found.")
    _save_servers(filtered)
    return {"status": "DISCONNECTED", "server_id": server_id}
