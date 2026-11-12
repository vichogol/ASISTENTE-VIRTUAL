"""Configuración común de pruebas unitarias.

Se fijan variables de entorno antes de importar la aplicación para que
`Settings` no dependa de un archivo `.env` real ni de servicios externos.
"""

import os

os.environ.setdefault("TURNSTILE_ENABLED", "false")
os.environ.setdefault("TURNSTILE_SECRET_KEY", "")
os.environ.setdefault("FREELLMAPI_API_KEY", "test-key")
os.environ.setdefault("RATE_LIMIT", "30/minute")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

import pytest  # noqa: E402

from app.core.rate_limit import limiter  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Evita que el contador de rate limit se filtre entre pruebas."""
    limiter.reset()
    yield
    limiter.reset()
