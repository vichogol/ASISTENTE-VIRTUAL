"""Pruebas unitarias del servicio RAG (app/services/rag.py)."""

import asyncio

import pytest

from app.config import settings
from app.services import rag


class FakeCollection:
    """Doble de prueba de la colección Chroma."""

    def __init__(self, documents, metadatas):
        self.documents = documents
        self.metadatas = metadatas
        self.last_n_results = None

    def query(self, query_embeddings, n_results):
        self.last_n_results = n_results
        assert query_embeddings == [[0.1, 0.2, 0.3]]
        return {"documents": [self.documents], "metadatas": [self.metadatas]}


@pytest.fixture
def fake_store(monkeypatch):
    collection = FakeCollection(
        documents=["Pregunta: ¿Cómo pago el permiso de circulación?\nRespuesta: En línea."],
        metadatas=[
            {"id": 12, "pregunta": "¿Cómo pago el permiso de circulación?", "direccion": "Dirección de Tránsito"}
        ],
    )
    monkeypatch.setattr(rag, "embed", lambda texts: [[0.1, 0.2, 0.3] for _ in texts])
    monkeypatch.setattr(rag, "get_collection", lambda: collection)
    return collection


def test_respuesta_incluye_fuentes_y_usa_top_k(fake_store, monkeypatch):
    capturado = {}

    async def fake_completion(system, user):
        capturado["system"] = system
        capturado["user"] = user
        return "Debes pagar en línea."

    monkeypatch.setattr(rag, "chat_completion", fake_completion)
    result = asyncio.run(rag.answer("¿Dónde pago el permiso de circulación?"))

    assert result["answer"] == "Debes pagar en línea."
    assert result["sources"] == [
        {"id": 12, "pregunta": "¿Cómo pago el permiso de circulación?", "direccion": "Dirección de Tránsito"}
    ]
    assert fake_store.last_n_results == settings.top_k
    assert "CONTEXTO:" in capturado["user"]
    assert "¿Dónde pago el permiso de circulación?" in capturado["user"]
    assert "SOLO en español" in capturado["system"]


def test_sin_contexto_usa_marcador(monkeypatch):
    monkeypatch.setattr(rag, "embed", lambda texts: [[0.1, 0.2, 0.3]])
    monkeypatch.setattr(rag, "get_collection", lambda: FakeCollection([], []))
    capturado = {}

    async def fake_completion(system, user):
        capturado["user"] = user
        return "No tengo esa información."

    monkeypatch.setattr(rag, "chat_completion", fake_completion)
    result = asyncio.run(rag.answer("consulta sin coincidencias"))

    assert "(sin contexto)" in capturado["user"]
    assert result["sources"] == []


def test_fallback_amigable_si_el_llm_falla(fake_store, monkeypatch):
    async def boom(system, user):
        raise RuntimeError("router caído")

    monkeypatch.setattr(rag, "chat_completion", boom)
    result = asyncio.run(rag.answer("consulta"))

    assert "No pude conectarme al servicio de IA" in result["answer"]
    assert "OIRS" in result["answer"]
    assert len(result["sources"]) == 1
