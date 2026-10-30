from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.core.rate_limit import limiter
from app.core.turnstile import verify_turnstile
from app.services.rag import answer

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str | None = None
    turnstile_token: str | None = None


class Source(BaseModel):
    id: int | str | None = None
    pregunta: str | None = None
    direccion: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = []


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.rate_limit)
async def chat(request: Request, req: ChatRequest):
    if settings.turnstile_enabled:
        if not req.turnstile_token or not await verify_turnstile(
            req.turnstile_token, request.client.host if request.client else None
        ):
            raise HTTPException(status_code=400, detail="Captcha inválido")
    msg = " ".join(req.message.split())
    result = await answer(msg)
    return result
