import uuid
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    READ = "READ"
    WRITE = "WRITE"
    EXTERNAL_SIDE_EFFECT = "EXTERNAL_SIDE_EFFECT"

class ToolSource(StrEnum):
    INTERNAL = "internal"
    MCP = "mcp"

class ToolDefinition(BaseModel):
    name: str = Field(description="Unique name of the tool")
    version: str = Field(default="1.0.0", description="Version of the tool")
    description: str = Field(description="Purpose of the tool")
    input_schema: dict[str, Any] = Field(description="JSON schema for inputs")
    output_schema: dict[str, Any] | None = Field(default=None, description="JSON schema for output")
    risk_level: RiskLevel = Field(default=RiskLevel.READ)
    requires_approval: bool = Field(default=False)
    idempotent: bool = Field(default=True)
    timeout_seconds: int = Field(default=30)
    retry_policy: dict[str, Any] | None = Field(default=None)
    organization_scoped: bool = Field(default=True)
    source: ToolSource = Field(default=ToolSource.INTERNAL)

class ToolContext(BaseModel):
    organization_id: uuid.UUID
    agent_run_id: uuid.UUID
    execution_id: str
    dry_run: bool = False
    idempotency_key: str | None = None
    user_id: uuid.UUID | None = None
    approved: bool = False

class ToolResult(BaseModel):
    status: Literal["succeeded", "failed"]
    result: dict[str, Any] | None = None
    error_type: str | None = None
    message: str | None = None
    retryable: bool = False

class ToolExecutionLifecycleEvent(BaseModel):
    execution_id: str
    tool_name: str
    status: str
    organization_id: uuid.UUID
    agent_run_id: uuid.UUID
    started_at: str
    duration_ms: int
