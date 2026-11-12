"""Pruebas de configuración y parámetros del asistente."""

from app.config import Settings


def test_valores_por_defecto():
    s = Settings(_env_file=None)
    assert s.top_k == 5
    assert s.freellmapi_model == "auto"
    assert s.embedding_model == "paraphrase-multilingual-MiniLM-L12-v2"
    assert s.turnstile_enabled is False
    assert s.rate_limit == "30/minute"


def test_cors_origins_multiple():
    s = Settings(_env_file=None, cors_origins="http://a.cl, http://b.cl ,")
    origins = [o.strip() for o in s.cors_origins.split(",") if o.strip()]
    assert origins == ["http://a.cl", "http://b.cl"]


def test_api_key_se_lee_desde_entorno(monkeypatch):
    monkeypatch.setenv("FREELLMAPI_API_KEY", "clave-de-prueba")
    s = Settings(_env_file=None)
    assert s.freellmapi_api_key == "clave-de-prueba"


def test_api_key_por_defecto_vacia(monkeypatch):
    monkeypatch.delenv("FREELLMAPI_API_KEY", raising=False)
    s = Settings(_env_file="archivo-inexistente.env")
    assert s.freellmapi_api_key == ""
