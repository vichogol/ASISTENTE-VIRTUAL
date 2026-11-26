
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
import sqlite3

from app.config import settings
from app.core.rate_limit import limiter
from app.core.turnstile import verify_turnstile
from app.services import learning
from app.services.place_catalog import PLACES
from app.services.rag import answer

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str | None = Field(default=None, min_length=1, max_length=100)
    turnstile_token: str | None = Field(default=None, max_length=2048)


class Source(BaseModel):
    id: int | str | None = None
    pregunta: str | None = None
    direccion: str | None = None
    categoria: str | None = None
    hoja: str | None = None
    revision: str | None = None


class Section(BaseModel):
    title: str
    lines: list[str]


class Link(BaseModel):
    label: str
    url: str


class Contact(BaseModel):
    unit: str
    address: str | None
    phone: str | None
    email: str | None
    url: str
    source_url: str
    building: str | None


class Referral(Contact):
    central: Contact | None = None


class Building(BaseModel):
    id: str
    name: str
    short_name: str
    address: str
    latitude: float | None
    longitude: float | None
    style: str
    services: list[str]
    source_url: str
    map_source: str | None
    photo_url: str | None = None
    photo_source: str | None = None
    photo_caption: str | None = None
    service: str | None = None


class Similarity(BaseModel):
    method: str
    score: float


class Suggestion(BaseModel):
    label: str
    question: str


class ChatResponse(BaseModel):
    answer: str
    intro: str | None = None
    sources: list[Source] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    actions: list[Link] = Field(default_factory=list)
    suggestions: list[Suggestion] = Field(default_factory=list)
    referral: Referral | None = None
    buildings: list[Building] = Field(default_factory=list)
    interaction_id: UUID | None = None
    match: Similarity | None = None


class FeedbackRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    helpful: bool = Field(strict=True)


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.rate_limit)
async def chat(request: Request, req: ChatRequest):
    if settings.turnstile_enabled:
        if not req.turnstile_token or not await verify_turnstile(
            req.turnstile_token, request.client.host if request.client else None
        ):
            raise HTTPException(status_code=400, detail="Captcha inválido")
    msg = " ".join(req.message.split())
    if not msg:
        raise HTTPException(status_code=422, detail="Escribe una consulta antes de enviarla.")
    if req.session_id is None:
        return await answer(msg)
    return await answer(msg, session=req.session_id)


@router.get("/buildings", response_model=list[Building])
async def buildings():
    return list(PLACES.values())


@router.put("/chat/{interaction_id}/feedback", status_code=204)
@limiter.limit(settings.rate_limit)
async def feedback(request: Request, interaction_id: UUID, req: FeedbackRequest):
    try:
        accepted = await run_in_threadpool(learning.rate, str(interaction_id), req.session_id, req.helpful)
    except (sqlite3.Error, OSError) as error:
        raise HTTPException(503, detail="Las valoraciones no están disponibles por el momento.") from error
    if not accepted:
        raise HTTPException(404, detail="No encontramos esa respuesta para tu sesión.")
