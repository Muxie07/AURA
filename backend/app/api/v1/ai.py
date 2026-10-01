from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.ai.routing.router import ModelRouter
from app.ai.schemas.generation import GenerationRequest, Message
from app.ai.services.llm import LLMService
from app.security.rate_limit import rate_limit_dependency

router = APIRouter()

class GenerateRequest(BaseModel):
    message: str = Field(..., description="The message to send to the AI.")

class GenerateResponse(BaseModel):
    text: str
    model: str
    provider: str
    usage: dict[str, int | float | None]

class ClassifyRequest(BaseModel):
    text: str = Field(..., description="The text to classify.")

class IntentResult(BaseModel):
    intent: str
    confidence: float

@router.post("/generate", response_model=GenerateResponse, dependencies=[Depends(rate_limit_dependency)])
async def test_generate(
    request: GenerateRequest,
) -> Any:
    """Test endpoint for normal generation."""
    llm_service = LLMService()

    gen_request = GenerationRequest(
        messages=[Message(role="user", content=request.message)],
        model=ModelRouter.get_model_for_task("general"),
        temperature=0.1,
    )

    result = await llm_service.generate(gen_request)
    return {
        "text": result.text,
        "model": result.model,
        "provider": result.provider,
        "usage": result.usage.model_dump(),
    }

@router.post("/classify", response_model=IntentResult, dependencies=[Depends(rate_limit_dependency)])
async def test_classify(
    request: ClassifyRequest,
) -> Any:
    """Test endpoint for structured generation."""
    llm_service = LLMService()

    gen_request = GenerationRequest(
        messages=[Message(role="user", content=request.text)],
        model=ModelRouter.get_model_for_task("classification"),
        temperature=0.0,
    )

    _, parsed = await llm_service.generate_structured(gen_request, IntentResult)
    return parsed
