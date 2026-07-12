from fastapi import APIRouter

from app.schemas import LLMProviderOut
from app.services.llm import list_providers

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/providers", response_model=list[LLMProviderOut])
def get_providers() -> list[LLMProviderOut]:
    return [
        LLMProviderOut(
            id=p.id,
            name=p.name,
            available=p.available,
            model=p.model,
            hint=p.hint,
        )
        for p in list_providers()
    ]
