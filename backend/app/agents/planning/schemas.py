from typing import Any

from pydantic import BaseModel, Field


class PlannedStep(BaseModel):
    id: str = Field(..., description="Unique step identifier (e.g. 'step_1')")
    type: str = Field(..., description="Type of action")
    description: str = Field(
        ..., description="Detailed description of what the step must accomplish"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="List of step IDs that must complete before this step"
    )
    required_tools: list[str] = Field(
        default_factory=list, description="Tools needed for this step"
    )
    risk: str = Field("LOW", description="Risk level (LOW, MEDIUM, HIGH)")
    expected_output: str = Field("", description="What this step should produce")
    verification_criteria: str = Field("", description="How to verify success")


class StructuredAgentPlan(BaseModel):
    goal: str = Field(..., description="The overall objective goal")
    steps: list[PlannedStep] = Field(..., description="The sequence/FAG of steps to execute")


class IntentUnderstanding(BaseModel):
    intent: str = Field(..., description="The classified primary intent of the user (e.g. 'search_customer', 'create_quotation', 'general_query').")
    entities: dict[str, Any] = Field(
        default_factory=dict, description="Extracted entities from the request (e.g. {'customer_name': 'Acme', 'action': 'create_quotation'})."
    )
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0 of this understanding.")
    requires_clarification: bool = Field(
        ..., description="True if the request is ambiguous (e.g. 'create one', 'do it') and the context is insufficient, requiring clarification."
    )
    clarification_question: str | None = Field(
        None, description="A concise question to ask the user if clarification is needed."
    )
    normalized_request: str = Field(
        ...,
        description="The user's request rewritten to fix typos, correct grammar, and resolve pronouns using conversation context. Do NOT guess destructive intents.",
    )
    candidate_tools: list[str] = Field(
        default_factory=list, description="List of tool names that might be relevant to satisfy this intent."
    )
    is_safe: bool = Field(
        ...,
        description="True if the request is safe. False if it implies a destructive action without explicit context.",
    )
    reasoning: str = Field(..., description="Reasoning for the safety and intent assessment.")
