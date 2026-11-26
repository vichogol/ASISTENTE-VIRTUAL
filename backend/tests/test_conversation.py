
import asyncio

import pytest

from app.services import rag


@pytest.mark.parametrize("message", ["Hola", "¡Buenas tardes!", "Hola, ¿cómo estás?", "Hola asistente", "Buenas, ¿qué tal?", "Hola, buenas tardes"])
def test_greetings_are_a_conversation_not_a_referral(message):
    result = asyncio.run(rag.answer(message, session="vecina"))
    assert result["intro"].startswith("¡Hola!") and "Peñalolín" in result["intro"]
    assert result["suggestions"] and not result["sources"]
    assert not result["referral"] and not result["buildings"]
    assert result["interaction_id"] is None


@pytest.mark.parametrize("message", ["¿Qué puedes hacer?", "Necesito ayuda", "Hola, ¿qué trámites hay?"])
def test_general_help_offers_official_questions(message):
    result = asyncio.run(rag.answer(message))
    assert "orientarte" in result["intro"]
    assert "licencia" in result["suggestions"][0]["question"]
    assert not result["referral"]


@pytest.mark.parametrize(
    ("message", "source_id"),
    [
        ("horario piscina", 4),
        ("renovar licencia", 255),
        ("como saco hora para renovar mi carnet de manejar", 340),
        ("pagar permiso del auto online", 791),
        ("precio permiso de circulasion", 788),
        ("talleres chimkowe", 519),
    ],
)
def test_brief_keywords_find_a_reviewed_faq(message, source_id):
    result = asyncio.run(rag.answer(message))
    assert result["sources"][0]["hoja"] == "Revisdas"
    assert result["sources"][0]["id"] == source_id
    assert not result["referral"]


@pytest.mark.parametrize("message", ["RSH", "carnet para manejar", "permiso online", "pagar permiso", "piscina", "donde reciclar"])
def test_incomplete_queries_ask_for_clarification(message):
    result = asyncio.run(rag.answer(message))
    assert "¿" in result["intro"]
    assert result["suggestions"] and not result["sources"]
    assert not result["referral"]


def test_greeting_with_a_question_keeps_the_answer_and_sources():
    result = asyncio.run(rag.answer("Hola, ¿cómo pago el permiso de circulación en línea?"))
    assert result["intro"].startswith("¡Hola!")
    assert result["sources"][0]["id"] == 791


@pytest.mark.parametrize("message", [
    "horario piscina durante feriado", "renovar licencia clase b en 2090",
    "¿Cuál es el estado de mi solicitud de licencia de conducir?",
])
def test_specific_unverified_qualifiers_never_receive_a_generic_faq_as_fact(message):
    result = asyncio.run(rag.answer(message))
    assert not result["sources"]
    assert result["referral"]


def test_broad_queries_outside_predefined_topics_offer_matching_questions():
    result = asyncio.run(rag.answer("becas"))
    assert result["suggestions"]
    assert all("beca" in option["question"].lower() for option in result["suggestions"])
    assert not result["sources"] and not result["referral"]


@pytest.mark.parametrize(("message", "detail"), [("horario", "recinto"), ("requisitos", "trámite"), ("trámites en línea", "en línea")])
def test_bare_intents_ask_for_the_procedure_or_place(message, detail):
    result = asyncio.run(rag.answer(message))
    assert detail in result["intro"]
    assert result["suggestions"] and not result["referral"]


@pytest.mark.parametrize("message", ["¿Quién eres?", "¿Cómo te llamas?", "Hola, ¿quién me responde?"])
def test_assistant_identity_offers_help_without_referral(message):
    result = asyncio.run(rag.answer(message))
    assert "Soy Peñalolín" in result["intro"]
    assert result["suggestions"] and not result["referral"] and not result["sources"]


@pytest.mark.parametrize(("message", "source_id"), [
    ("¿Cómo pago el permiso de ciruclación en línea?", 791),
    ("horario de la pisicna temperada", 4),
])
def test_fuzzy_retrieval_resolves_distinctive_typos(message, source_id):
    result = asyncio.run(rag.answer(message))
    assert result["sources"][0]["id"] == source_id
    assert result["match"]["method"] == "difusa"


def test_new_recinto_has_a_published_address_and_navigation():
    result = asyncio.run(rag.answer("¿Dónde queda ChileAtiende?"))
    place, = result["buildings"]
    assert place["id"] == "chileatiende"
    assert "Las Torres 5555" in place["address"]
    assert not result["referral"]
