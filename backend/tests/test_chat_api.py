"""Pruebas de integración del contrato HTTP (app/api/chat.py + app/main.py).

El servicio RAG se reemplaza por un doble de prueba: no se carga el modelo de
embeddings ni se invoca un LLM real.
"""

import pytest
from fastapi.testclient import TestClient

from app.api import chat as chat_module
from app.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_answer(monkeypatch):
    async def _answer(message: str) -> dict:
        return {
            "answer": f"eco: {message}",
            "sources": [{"id": 1, "pregunta": "P", "direccion": "D"}],
        }

    monkeypatch.setattr(chat_module, "answer", _answer)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_chat_ok_y_normaliza_espacios():
    r = client.post("/api/chat", json={"message": "  hola   mundo  "})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "eco: hola mundo"
    assert body["sources"][0]["pregunta"] == "P"


def test_mensaje_vacio_rechazado():
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_mensaje_demasiado_largo_rechazado():
    assert client.post("/api/chat", json={"message": "x" * 1001}).status_code == 422


def test_rate_limit_bloquea_peticion_31():
    for i in range(30):
        r = client.post("/api/chat", json={"message": f"consulta {i}"})
        assert r.status_code == 200, f"falló en la petición {i + 1}"
    r = client.post("/api/chat", json={"message": "una más"})
    assert r.status_code == 429
    assert "Demasiadas solicitudes" in r.json()["detail"]


def test_turnstile_habilitado_sin_token_devuelve_400(monkeypatch):
    monkeypatch.setattr(settings, "turnstile_enabled", True)
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret")
    r = client.post("/api/chat", json={"message": "hola"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Captcha inválido"


def test_turnstile_token_invalido_devuelve_400(monkeypatch):
    async def _verify(token, ip=None):
        return False

    monkeypatch.setattr(settings, "turnstile_enabled", True)
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret")
    monkeypatch.setattr(chat_module, "verify_turnstile", _verify)
    r = client.post("/api/chat", json={"message": "hola", "turnstile_token": "malo"})
    assert r.status_code == 400


def test_turnstile_token_valido_permite_paso(monkeypatch):
    async def _verify(token, ip=None):
        return True

    monkeypatch.setattr(settings, "turnstile_enabled", True)
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret")
    monkeypatch.setattr(chat_module, "verify_turnstile", _verify)
    r = client.post("/api/chat", json={"message": "hola", "turnstile_token": "ok"})
    assert r.status_code == 200
    assert r.json()["answer"] == "eco: hola"
