from pydantic import BaseModel, Field


class PlannedStep(BaseModel):
    id: str = Field(..., description="Unique step identifier (e.g. 'step_1')")
    type: str = Field(..., description="Type of action")
    description: str = Field(..., description="Detailed description of what the step must accomplish")
    dependencies: list[str] = Field(default_factory=list, description="List of step IDs that must complete before this step")
    required_tools: list[str] = Field(default_factory=list, description="Tools needed for this step")
    risk: str = Field("LOW", description="Risk level (LOW, MEDIUM, HIGH)")
    expected_output: str = Field("", description="What this step should produce")
    verification_criteria: str = Field("", description="How to verify success")

class StructuredAgentPlan(BaseModel):
    goal: str = Field(..., description="The overall objective goal")
    steps: list[PlannedStep] = Field(..., description="The sequence/FAG of steps to execute")

class IntentUnderstanding(BaseModel):
    normalized_request: str = Field(..., description="The user's request rewritten safely, grammatically correct, and disambiguated.")
    is_safe: bool = Field(..., description="True if the request is safe and clear. False if it is ambiguous, destructive, or lacks required context for a write operation.")
    reasoning: str = Field(..., description="Reasoning for the safety assessment.")
    requires_clarification: bool = Field(..., description="True if the request is ambiguous and needs user clarification.")
    clarification_question: str | None = Field(None, description="The question to ask the user if clarification is needed.")
