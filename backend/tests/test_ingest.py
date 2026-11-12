"""Pruebas del pipeline de ingesta (scripts/ingest.py).

Se valida la regla de negocio de filtrado: solo se indexan preguntas activas.
"""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ingest.py"


@pytest.fixture(scope="module")
def ingest():
    spec = importlib.util.spec_from_file_location("ingest_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (1, True),
        (1.0, True),
        (0, False),
        (0.0, False),
        ("1", True),
        ("0", False),
        (float("nan"), True),
        (None, True),
        ("texto", True),
    ],
)
def test_is_active(ingest, valor, esperado):
    assert ingest.is_active(valor) is esperado


def test_is_active_serie_pandas(ingest):
    serie = pd.Series([1, 0, None, float("nan")])
    assert [ingest.is_active(v) for v in serie] == [True, False, True, True]
