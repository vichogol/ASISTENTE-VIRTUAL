
from app.config import settings
from app.services import retrieval, vector_store
from app.services.knowledge import FAQ


def record_faq():
    return FAQ("Revisdas:1", 1, "Revisdas", True, "Horario cursos piscina temperada intensiva natación infancia verano",
               "Corporación Deportes", "", "", ("Consulta la programación municipal.",), ())


def test_reviewed_promotion_recovers_a_nearby_formulation_with_independent_evidence():
    faq = record_faq()
    engine = retrieval.Retriever((faq,), "fixture")
    question = "Horario cursos piscina temperada profesores"
    assert retrieval.confident_match(engine.rank(question, {})) is None
    learned = {faq.key: .68}
    match = retrieval.confident_match(engine.rank(question, learned))
    assert match and match.faq == faq and match.method == "aprendida"
    assert retrieval.confident_match(engine.rank("Costo cursos piscina temperada profesores", learned)) is None


def test_semantic_similarity_checks_workbook_and_model_versions(monkeypatch):
    monkeypatch.setattr(settings, "semantic_search", True)
    monkeypatch.setattr(vector_store, "embed", lambda texts: [[.1, .2]])

    class Collection:
        metadata = {"faq_revision": "actual", "embedding_model": settings.embedding_model}

        @staticmethod
        def count():
            return 1

        @staticmethod
        def query(query_embeddings, n_results):
            assert query_embeddings == [[.1, .2]] and n_results == 1
            return {"ids": [["Revisdas:1"]], "distances": [[.25]]}

    monkeypatch.setattr(vector_store, "get_collection", lambda revision: Collection())
    assert retrieval.vector_scores("pregunta", "actual") == {"Revisdas:1": .75}
    assert retrieval.vector_scores("pregunta", "otro") == {}


def test_retrieval_uses_known_colloquial_paraphrase():
    from app.services.rag import get_index

    ranked = get_index().rank("¿Cuándo abren las horas para renovar mi carnet de manejar?", {})
    result = retrieval.confident_match(ranked)
    assert result and result.faq.key == "Revisdas:287" and result.method == "similar"
