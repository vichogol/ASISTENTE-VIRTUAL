
import json
from dataclasses import replace

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.knowledge import FAQ
from app.services.learning import database, learned_scores, rate, record
from app.services.retrieval import Match

FAQ_FIXTURE = FAQ("Revisdas:4", 4, "Revisdas", True, "Horario Piscina Municipal",
                  "Deportes", "", "", ("Consulta el horario publicado.",), ())
QUESTION = "¿Cuál es el horario de la piscina temperada?"


def configure(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "learning_enabled", True)
    monkeypatch.setattr(settings, "learning_path", str(tmp_path / "learn.sqlite"))


def test_promotes_and_revokes_with_independent_sessions(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    match = Match(FAQ_FIXTURE, .93, "equivalente", True)
    first = record(QUESTION, "vecina-a", [match], match)
    repeated = record(QUESTION, "vecina-a", [match], match)
    assert not rate(first, "vecina-b", True)
    assert rate(first, "vecina-a", True)
    assert rate(repeated, "vecina-a", True)
    second = record(QUESTION, "vecina-b", [match], match)
    assert rate(second, "vecina-b", True)
    assert learned_scores(QUESTION, {FAQ_FIXTURE.key: FAQ_FIXTURE}) == {}
    third = record(QUESTION, "vecina-c", [match], match)
    assert rate(third, "vecina-c", True)
    assert learned_scores(QUESTION, {FAQ_FIXTURE.key: FAQ_FIXTURE}) == {FAQ_FIXTURE.key: .93}
    updated_faq = replace(FAQ_FIXTURE, lines=("Ficha actualizada.",))
    assert learned_scores(QUESTION, {FAQ_FIXTURE.key: updated_faq}) == {}
    assert rate(third, "vecina-c", False)
    assert learned_scores(QUESTION, {FAQ_FIXTURE.key: FAQ_FIXTURE}) == {}
    with database() as db:
        events = db.execute("SELECT action, evidence FROM promotion_events ORDER BY id").fetchall()
    assert [event["action"] for event in events] == ["promovida", "revocada"]
    assert set(json.loads(events[0]["evidence"])["a_favor"]) == {repeated, second, third}


def test_low_confidence_and_recognizable_contact_are_not_promoted(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    weak = Match(FAQ_FIXTURE, .73, "similar", True)
    for session in ("a", "b", "c"):
        assert rate(record(QUESTION, session, [weak], weak), session, True)
    match = replace(weak, score=.95)
    interaction = record("Mi correo es vecina@example.com y mi RUT es 12.345.678-9", "a", [match], match)
    with database() as db:
        row = db.execute("SELECT * FROM interactions WHERE id=?", (interaction,)).fetchone()
        assert db.execute("SELECT count(*) FROM promoted").fetchone()[0] == 0
    assert "example.com" not in row["question"] and "345.678" not in row["question"]
    assert not row["alias"] and row["faq_key"] is None
    assert row["session_hash"] != "a"


def test_feedback_http_and_catalog(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    client = TestClient(app)
    result = client.post("/api/chat", json={"message": QUESTION, "session_id": "vecina"}).json()
    url = f"/api/chat/{result['interaction_id']}/feedback"
    assert client.put(url, json={"session_id": "distinta", "helpful": True}).status_code == 404
    assert client.put(url, json={"session_id": "vecina", "helpful": True}).status_code == 204
    assert client.put(url, json={"session_id": "vecina", "helpful": True}).status_code == 204
    assert client.put(url, json={"session_id": "vecina", "helpful": "sí"}).status_code == 422
    assert client.post("/api/chat", json={"message": "   "}).status_code == 422
    places = client.get("/api/buildings").json()
    assert len(places) == len({place["id"] for place in places}) == 15
    assert {place["id"] for place in places} >= {"caf", "bodega", "mediacion", "chileatiende", "registro-civil"}
    assert all(place["address"] and place["source_url"] for place in places)
    assert all((place["latitude"] is None) == (place["longitude"] is None) for place in places)
    mapped = [place for place in places if place["latitude"] is not None]
    assert all(-34 < place["latitude"] < -33 and -71 < place["longitude"] < -70 for place in mapped)
    consistorial = next(place for place in places if place["id"] == "consistorial")
    assert consistorial["photo_url"] == "/recintos/consistorial.png"
