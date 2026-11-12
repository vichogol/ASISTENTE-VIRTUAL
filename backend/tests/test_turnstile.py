"""Pruebas del verificador Cloudflare Turnstile (app/core/turnstile.py)."""

import asyncio

from app.config import settings
from app.core import turnstile as turnstile_mod


def test_sin_secret_key_permite_paso():
    original = settings.turnstile_secret_key
    settings.turnstile_secret_key = ""
    try:
        assert asyncio.run(turnstile_mod.verify_turnstile("cualquier-token")) is True
    finally:
        settings.turnstile_secret_key = original


def test_token_valido(monkeypatch):
    class FakeResponse:
        def json(self):
            return {"success": True}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, data=None):
            assert url.endswith("/siteverify")
            assert data["response"] == "token-ok"
            return FakeResponse()

    monkeypatch.setattr(turnstile_mod.settings, "turnstile_secret_key", "secret-test")
    monkeypatch.setattr(turnstile_mod.httpx, "AsyncClient", FakeClient)
    assert asyncio.run(turnstile_mod.verify_turnstile("token-ok", "127.0.0.1")) is True


def test_token_invalido(monkeypatch):
    class FakeResponse:
        def json(self):
            return {"success": False, "error-codes": ["invalid-input-response"]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, data=None):
            return FakeResponse()

    monkeypatch.setattr(turnstile_mod.settings, "turnstile_secret_key", "secret-test")
    monkeypatch.setattr(turnstile_mod.httpx, "AsyncClient", FakeClient)
    assert asyncio.run(turnstile_mod.verify_turnstile("token-malo")) is False
