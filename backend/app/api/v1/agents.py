"""
AURA API v1 - Enterprise Agents Directory & Studio.
Provides persistent catalog management, configuration, status toggling, and testing for enterprise agents.
"""

import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUserDep

router = APIRouter(prefix="/agents", tags=["Agents"])

DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "enterprise_agents.json"
)

DEFAULT_ENTERPRISE_AGENTS = [
    {
        "id": "agent-sales-ops",
        "name": "Sales Quotation & Pricing Specialist",
        "description": "Calculates corporate discounts, parses Cloud Infotech hardware price books, and drafts verified quotations.",
        "purpose": "B2B Quotation generation & hardware price auditing",
        "status": "ACTIVE",
        "model_provider": "google",
        "model_name": "gemini-2.5-flash",
        "system_prompt": (
            "You are the official enterprise Sales Operations Agent for AURA.\n"
            "Your responsibility is to assist sales leads and account executives with accurate quotation generation,\n"
            "discount rule enforcement, hardware model matching from the Cloud Infotech catalog, and GST tax invoice structuring.\n\n"
            "Strict Rules:\n"
            "1. Always calculate 18% GST on Indian B2B technology transactions.\n"
            "2. If discounts exceed 20%, explicitly require Senior Sales Director approval.\n"
            "3. Validate hardware availability and standard 3-year warranty status before finalizing quotations."
        ),
        "temperature": 0.2,
        "max_tokens": 2048,
        "assigned_tools": [
            "quotation.create_draft",
            "quotation.calculate_pricing",
            "invoice.generate",
            "customer.search",
        ],
        "assigned_tools_count": 4,
        "knowledge_bases": ["kb-cloud-infotech", "kb-pricing-policy"],
        "knowledge_bases_count": 2,
        "last_execution": "10 min ago",
        "success_rate": "98.4%",
        "owner": "Operations Team",
        "risk_tier": "MEDIUM",
        "require_human_approval": True,
        "rate_limit_per_minute": 30,
        "timeout_seconds": 45,
        "created_at": "2026-10-01T00:00:00Z",
    },
    {
        "id": "agent-invoice-gen",
        "name": "Tax Invoicing & Financial Settlement Agent",
        "description": "Generates official GST compliant invoices with itemized HSN/SAC codes and 18% tax calculations.",
        "purpose": "Automated invoice issuance with human-in-the-loop validation",
        "status": "ACTIVE",
        "model_provider": "google",
        "model_name": "gemini-2.5-flash",
        "system_prompt": "You are the Tax Invoicing & Financial Settlement Agent. Ensure statutory compliance with Indian GST rules.",
        "temperature": 0.1,
        "max_tokens": 2048,
        "assigned_tools": ["invoice.generate", "quotation.calculate_pricing", "customer.search"],
        "assigned_tools_count": 3,
        "knowledge_bases": ["kb-tax-compliance"],
        "knowledge_bases_count": 1,
        "last_execution": "2 hours ago",
        "success_rate": "100%",
        "owner": "Finance & Compliance",
        "risk_tier": "HIGH",
        "require_human_approval": True,
        "rate_limit_per_minute": 20,
        "timeout_seconds": 60,
        "created_at": "2026-10-05T00:00:00Z",
    },
    {
        "id": "agent-knowledge-rag",
        "name": "Enterprise Knowledge & Policy Researcher",
        "description": "Executes hybrid dense vector and BM25 sparse retrieval over internal corporate documentation.",
        "purpose": "Internal policy, catalog, and documentation lookup",
        "status": "ACTIVE",
        "model_provider": "google",
        "model_name": "gemini-2.5-flash",
        "system_prompt": "You are the Enterprise Policy and Documentation Specialist. Ground every answer in retrieved knowledge bases.",
        "temperature": 0.1,
        "max_tokens": 1500,
        "assigned_tools": ["mcp.product.search", "customer.search"],
        "assigned_tools_count": 2,
        "knowledge_bases": ["kb-cloud-infotech", "kb-pricing-policy", "kb-tax-compliance"],
        "knowledge_bases_count": 3,
        "last_execution": "45 min ago",
        "success_rate": "99.1%",
        "owner": "Knowledge Management",
        "risk_tier": "LOW",
        "require_human_approval": False,
        "rate_limit_per_minute": 60,
        "timeout_seconds": 30,
        "created_at": "2026-10-08T00:00:00Z",
    },
    {
        "id": "agent-mcp-orchestrator",
        "name": "Distributed MCP Tool Bridge",
        "description": "Executes external standardized MCP tools over SSE and JSON-RPC protocols with sandbox verification.",
        "purpose": "Connecting third-party inventory and CRM endpoints safely",
        "status": "ACTIVE",
        "model_provider": "google",
        "model_name": "gemini-2.5-flash",
        "system_prompt": "You are the MCP Orchestrator. Safely route tool invocations across registered MCP SSE endpoints.",
        "temperature": 0.0,
        "max_tokens": 1024,
        "assigned_tools": ["mcp.product.search", "utcp.warehouse.stock_lookup", "customer.search"],
        "assigned_tools_count": 3,
        "knowledge_bases": [],
        "knowledge_bases_count": 0,
        "last_execution": "3 hours ago",
        "success_rate": "96.5%",
        "owner": "Platform Engineering",
        "risk_tier": "MEDIUM",
        "require_human_approval": False,
        "rate_limit_per_minute": 45,
        "timeout_seconds": 30,
        "created_at": "2026-10-12T00:00:00Z",
    },
    {
        "id": "agent-eval-auditor",
        "name": "Response Faithfulness & Safety Gate",
        "description": "Calculates Ragas groundedness, citation coverage, and latency metrics across agent execution traces.",
        "purpose": "Continuous evaluation and safety auditing",
        "status": "ACTIVE",
        "model_provider": "heuristic",
        "model_name": "adaptive-hybrid-v1",
        "system_prompt": "You are the Evaluation and Quality Gate Agent. Validate faithfulness, factual grounding, and compliance.",
        "temperature": 0.0,
        "max_tokens": 1024,
        "assigned_tools": [],
        "assigned_tools_count": 0,
        "knowledge_bases": ["kb-pricing-policy"],
        "knowledge_bases_count": 1,
        "last_execution": "1 day ago",
        "success_rate": "100%",
        "owner": "AI Governance",
        "risk_tier": "LOW",
        "require_human_approval": False,
        "rate_limit_per_minute": 100,
        "timeout_seconds": 20,
        "created_at": "2026-10-15T00:00:00Z",
    },
]


def _load_agents() -> list[dict[str, Any]]:
    if os.path.exists(DATA_FILE_PATH):
        try:
            with open(DATA_FILE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Initialize with defaults
    _save_agents(DEFAULT_ENTERPRISE_AGENTS)
    return DEFAULT_ENTERPRISE_AGENTS


def _save_agents(agents: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(DATA_FILE_PATH), exist_ok=True)
    with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(agents, f, indent=2)


class AgentCreateOrUpdateRequest(BaseModel):
    id: str | None = None
    name: str
    description: str
    purpose: str
    status: str = "ACTIVE"
    model_provider: str = "google"
    model_name: str = "gemini-2.5-flash"
    system_prompt: str = ""
    temperature: float = 0.2
    max_tokens: int = 2048
    assigned_tools: list[str] = Field(default_factory=list)
    knowledge_bases: list[str] = Field(default_factory=list)
    risk_tier: str = "MEDIUM"
    require_human_approval: bool = True
    rate_limit_per_minute: int = 30
    timeout_seconds: int = 45


@router.get("", summary="List all configured Enterprise Agents")
async def list_agents(
    current_user: CurrentUserDep,
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None,
) -> dict[str, Any]:
    agents = _load_agents()
    if status_filter and status_filter.upper() != "ALL":
        agents = [a for a in agents if a.get("status", "").upper() == status_filter.upper()]
    if search:
        s = search.lower()
        agents = [
            a
            for a in agents
            if s in a.get("name", "").lower()
            or s in a.get("description", "").lower()
            or s in a.get("purpose", "").lower()
            or s in a.get("model_name", "").lower()
        ]
    return {"agents": agents, "total": len(agents)}


@router.get("/{agent_id}", summary="Get agent details by ID")
async def get_agent(agent_id: str, current_user: CurrentUserDep) -> dict[str, Any]:
    agents = _load_agents()
    agent = next((a for a in agents if a["id"] == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    return {"agent": agent}


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a new Enterprise Agent")
async def create_agent(
    req: AgentCreateOrUpdateRequest, current_user: CurrentUserDep
) -> dict[str, Any]:
    agents = _load_agents()
    new_id = req.id or f"agent-{uuid.uuid4().hex[:8]}"

    existing = next((a for a in agents if a["id"] == new_id), None)
    if existing:
        raise HTTPException(status_code=400, detail=f"Agent with ID '{new_id}' already exists.")

    new_agent = {
        "id": new_id,
        "name": req.name,
        "description": req.description,
        "purpose": req.purpose,
        "status": req.status.upper(),
        "model_provider": req.model_provider,
        "model_name": req.model_name,
        "system_prompt": req.system_prompt,
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
        "assigned_tools": req.assigned_tools,
        "assigned_tools_count": len(req.assigned_tools),
        "knowledge_bases": req.knowledge_bases,
        "knowledge_bases_count": len(req.knowledge_bases),
        "last_execution": "Never",
        "success_rate": "100%",
        "owner": current_user.email or "Platform Operator",
        "risk_tier": req.risk_tier.upper(),
        "require_human_approval": req.require_human_approval,
        "rate_limit_per_minute": req.rate_limit_per_minute,
        "timeout_seconds": req.timeout_seconds,
        "created_at": datetime.now(UTC).isoformat(),
    }
    agents.insert(0, new_agent)
    _save_agents(agents)
    return {"status": "CREATED", "agent": new_agent}


@router.put("/{agent_id}", summary="Update an existing Enterprise Agent")
async def update_agent(
    agent_id: str, req: AgentCreateOrUpdateRequest, current_user: CurrentUserDep
) -> dict[str, Any]:
    agents = _load_agents()
    idx = next((i for i, a in enumerate(agents) if a["id"] == agent_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    agent = agents[idx]
    agent.update(
        {
            "name": req.name,
            "description": req.description,
            "purpose": req.purpose,
            "status": req.status.upper(),
            "model_provider": req.model_provider,
            "model_name": req.model_name,
            "system_prompt": req.system_prompt,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "assigned_tools": req.assigned_tools,
            "assigned_tools_count": len(req.assigned_tools),
            "knowledge_bases": req.knowledge_bases,
            "knowledge_bases_count": len(req.knowledge_bases),
            "risk_tier": req.risk_tier.upper(),
            "require_human_approval": req.require_human_approval,
            "rate_limit_per_minute": req.rate_limit_per_minute,
            "timeout_seconds": req.timeout_seconds,
            "updated_at": datetime.now(UTC).isoformat(),
        }
    )
    agents[idx] = agent
    _save_agents(agents)
    return {"status": "UPDATED", "agent": agent}


@router.patch("/{agent_id}/status", summary="Toggle Agent Status (ACTIVE / PAUSED)")
async def toggle_agent_status(agent_id: str, current_user: CurrentUserDep) -> dict[str, Any]:
    agents = _load_agents()
    idx = next((i for i, a in enumerate(agents) if a["id"] == agent_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    current_status = agents[idx].get("status", "ACTIVE")
    new_status = "PAUSED" if current_status == "ACTIVE" else "ACTIVE"
    agents[idx]["status"] = new_status
    _save_agents(agents)
    return {"status": "UPDATED", "agent_id": agent_id, "new_status": new_status}


@router.delete("/{agent_id}", summary="Decommission an Enterprise Agent")
async def delete_agent(agent_id: str, current_user: CurrentUserDep) -> dict[str, Any]:
    agents = _load_agents()
    filtered = [a for a in agents if a["id"] != agent_id]
    if len(filtered) == len(agents):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    _save_agents(filtered)
    return {"status": "DELETED", "agent_id": agent_id}
