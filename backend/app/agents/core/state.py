import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentNodeState(StrEnum):
    """Explicit lifecycle states for the state machine."""
    CREATED = "CREATED"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    RETRIEVING = "RETRIEVING"
    READY_TO_EXECUTE = "READY_TO_EXECUTE"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    DIAGNOSING = "DIAGNOSING"
    REPLANNING = "REPLANNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"

class FailureCategory(StrEnum):
    TRANSIENT = "TRANSIENT"
    VALIDATION = "VALIDATION"
    AUTHORIZATION = "AUTHORIZATION"
    NOT_FOUND = "NOT_FOUND"
    BUSINESS_RULE = "BUSINESS_RULE"
    LLM_FAILURE = "LLM_FAILURE"
    TOOL_FAILURE = "TOOL_FAILURE"
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"

class AgentError(BaseModel):
    category: FailureCategory
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class AgentPlanStep(BaseModel):
    id: str
    type: str
    description: str
    dependencies: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    risk: str = "LOW"
    expected_output: str = ""
    verification_criteria: str = ""
    status: str = "pending"

class AgentPlan(BaseModel):
    goal: str
    steps: list[AgentPlanStep]

class AgentAction(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str
    description: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: str = "PENDING"

class ActionVerification(BaseModel):
    success: bool
    confidence: float
    issues: list[str] = Field(default_factory=list)

class ActionHistoryItem(BaseModel):
    action: AgentAction
    result: dict[str, Any] | None = None
    verification: ActionVerification | None = None
    error: AgentError | None = None
    started_at: datetime
    completed_at: datetime | None = None


class AgentLimits(BaseModel):
    max_replan_attempts: int = 3
    max_tool_calls: int = 15
    max_retries: int = 5
    overall_timeout_seconds: int = 300

class AgentState(BaseModel):
    limits: AgentLimits = Field(default_factory=AgentLimits)
    """Strongly typed state for the agent workflow."""
    run_id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    conversation_id: uuid.UUID

    # Input
    original_request: str
    normalized_request: str | None = None

    # Flow state
    status: AgentNodeState = AgentNodeState.CREATED
    current_step: str | None = None

    # Complex state
    plan: AgentPlan | None = None
    current_actions: list[AgentAction] = Field(default_factory=list)
    action_history: list[ActionHistoryItem] = Field(default_factory=list)
    retrieved_context: list[dict[str, Any]] = Field(default_factory=list)

    # Outputs
    final_response: str | None = None
    errors: list[AgentError] = Field(default_factory=list)

    # Limits & Counters
    retry_count: int = 0
    iteration_count: int = 0
    replans: int = 0

    # Token Tracking
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # Timestamps
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def add_error(self, category: FailureCategory, message: str, details: dict[str, Any] | None = None) -> None:
        self.errors.append(
            AgentError(category=category, message=message, details=details or {})
        )
        self.status = AgentNodeState.FAILED
