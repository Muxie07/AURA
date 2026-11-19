from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.tools.schemas import RiskLevel


class UTCPTransportType(StrEnum):
    HTTP = "http"
    WEBSOCKET = "websocket"
    SSE = "sse"


class UTCPAuthType(StrEnum):
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"
    HEADER = "header"


class UTCPAuthConfig(BaseModel):
    auth_type: UTCPAuthType = Field(default=UTCPAuthType.NONE)
    token: str | None = None
    header_name: str | None = Field(default="X-API-Key")
    username: str | None = None
    password: str | None = None


class UTCPToolSpec(BaseModel):
    name: str = Field(description="Unique tool identifier")
    description: str = Field(default="", description="Function documentation for LLM")
    endpoint: str = Field(description="Relative or absolute path for this tool")
    method: str = Field(default="POST", description="HTTP Method (GET, POST, PUT, DELETE)")
    input_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for arguments"
    )
    output_schema: dict[str, Any] | None = None
    risk_level: RiskLevel = Field(default=RiskLevel.READ)
    timeout_seconds: int = Field(default=30)
    idempotent: bool = Field(default=True)
    headers: dict[str, str] = Field(default_factory=dict)


class UTCPManifest(BaseModel):
    utcp_version: str = Field(default="1.0.0")
    name: str = Field(description="Namespace or system name")
    description: str = Field(default="")
    base_url: str = Field(description="Base URL of the service hosting the tools")
    transport: UTCPTransportType = Field(default=UTCPTransportType.HTTP)
    auth: UTCPAuthConfig = Field(default_factory=UTCPAuthConfig)
    tools: list[UTCPToolSpec] = Field(default_factory=list)
