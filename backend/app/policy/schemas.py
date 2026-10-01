import uuid
from enum import StrEnum

from pydantic import BaseModel


class PolicyDecision(StrEnum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


class PolicyContext(BaseModel):
    organization_id: uuid.UUID
    user_id: uuid.UUID | None
    tool_name: str
    risk_level: str
    arguments: dict
    permissions: list[str]


class PolicyRuleResult(BaseModel):
    decision: PolicyDecision
    reason: str
