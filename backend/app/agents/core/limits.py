from pydantic_settings import BaseSettings


class AgentLimits(BaseSettings):
    max_agent_iterations: int = 15
    max_tool_calls: int = 10
    max_retries: int = 3
    agent_timeout_seconds: int = 300
    max_plan_steps: int = 10


limits = AgentLimits()
