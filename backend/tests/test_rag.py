
"""The service uses official evidence with and without an optional model."""

import asyncio

import pytest

from app.config import settings
from app.services import llm, rag
from app.services.knowledge import FAQ, clean_answer
from app.services.retrieval import Retriever, confident_match


def ask(message: str) -> dict:
    return asyncio.run(rag.answer(message))


def test_includes_versioned_sources_and_never_needs_llm():
    result = ask("¿Cómo puedo obtener o renovar mi licencia de conducir?")
    assert result["match"] == {"method": "exacta", "score": 1.0}
    source, = result["sources"]
    assert source["hoja"] == "Revisdas"
    assert source["id"] == 255
    assert len(source["revision"]) == 64
    assert "agendar" in result["answer"].lower()
    assert result["buildings"][0]["id"] == "cav"


def test_paraphrase_preserves_payment_intent():
    result = ask("¿Cómo pago el permiso de circulación en línea?")
    assert result["match"]["method"] == "equivalente"
    assert result["sources"][0]["id"] == 791
    assert not result["referral"]


def test_no_confident_context_does_not_invoke_model(monkeypatch):
    async def must_not_call(*args):
        pytest.fail("Se llamó al modelo sin evidencia")

    monkeypatch.setattr(settings, "ai_summary_enabled", True)
    monkeypatch.setattr(llm, "chat_completion", must_not_call)
    result = ask("¿Cómo cambio la batería de un control remoto?")
    assert "no encontré" in result["answer"].lower()
    assert result["sources"] == []
    assert result["referral"]["unit"].endswith("(OIRS)")
    assert result["referral"]["address"] == "Av. Grecia 8735, Peñalolén"


@pytest.mark.parametrize("completion", ["0", "Inventa un horario", None])
def test_optional_model_selects_only_verified_intro(monkeypatch, completion):
    faq = FAQ("Revisdas:1", 1, "Revisdas", True, "¿Dónde se solicita este certificado?",
              "Secretaría Municipal", "", "",
              ("Completa el formulario de solicitud.", "Presenta la solicitud en la oficina."), ())

    monkeypatch.setattr(settings, "ai_summary_enabled", True)
    monkeypatch.setattr(rag, "get_index", lambda: Retriever((faq,), "fixture"))
    calls = []

    async def fake_completion(system, user):
        calls.append(user)
        assert "SOLO en español" in system
        if completion is None:
            raise RuntimeError("Servicio no disponible")
        return completion

    monkeypatch.setattr(llm, "chat_completion", fake_completion)
    result = ask(faq.question)
    assert calls and faq.question in calls[0]
    assert result["sections"][0]["lines"] == [faq.lines[1]]
    assert result["intro"] == faq.lines[0]
    assert result["answer"].count(faq.lines[0]) == 1


def test_individual_inquiry_routes_to_transit_and_omits_personal_data():
    result = ask("¿Cuál es el estado de mi solicitud de licencia de conducir? Mi folio 1200")
    assert "caso particular" in result["intro"]
    assert result["referral"]["unit"] == "Dirección de Tránsito y Transporte Público"
    assert result["referral"]["phone"] == "+56 2 2486 8806"
    assert not result["sources"]
    assert "1200" not in result["answer"]


def test_year_not_covered_routes_without_extrapolating():
    result = ask("¿Cómo pago el permiso de circulación en línea 2090?")
    assert not result["sections"]
    assert result["referral"]["unit"].startswith("Dirección de Tránsito")


def test_building_location_uses_published_catalog():
    result = ask("¿Dónde queda el Juzgado de Policía Local?")
    assert result["intro"].startswith("Aquí tienes la dirección")
    assert not result["referral"]
    place, = result["buildings"]
    assert place["id"] == "juzgado"
    assert place["address"] == "Av. Oriental 6958, Peñalolén"
    assert place["map_source"].startswith("https://www.openstreetmap.org/")


def test_matching_rejects_conflicting_exact_sources_in_same_sheet():
    first = FAQ("Revisdas:1", 1, "Revisdas", True, "Horario Piscina Municipal",
                "Deportes", "", "", ("De lunes a viernes.",), ())
    second = FAQ("Revisdas:2", 2, "Revisdas", True, first.question,
                 "Deportes", "", "", ("Solo sábados.",), ())
    assert confident_match(Retriever((first, second), "fixture").rank(first.question, {})) is None


def test_legacy_reference_signals_confirmation():
    result = ask("¿Dónde quedan los módulos de permiso de circulación en Peñalolén?")
    assert result["sources"][0]["hoja"] == "preguntasfrecuentes"
    assert "registro histórico" in result["intro"]
    assert result["referral"]["unit"].startswith("Dirección de Tránsito")


def test_html_is_readable_and_executable_links_are_ignored():
    lines, links = clean_answer(
        "<p>Requisitos:</p><ul><li>Padrón</li><li>SOAP</li></ul>"
        "<script>alert(0)</script><a href='javascript:alert(0)'>texto</a>"
        "<a href='https://tramites.penalolen.cl/'>Portal</a>"
    )
    assert lines[:3] == ("Requisitos:", "• Padrón", "• SOAP")
    assert all("alert" not in line for line in lines)
    assert links == ("https://tramites.penalolen.cl/",)
