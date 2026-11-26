
"""SQLite interaction ledger. Learned entries reference versioned official answers."""

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.services.knowledge import FAQ, normalize, redact
from app.services.retrieval import Match, tokens

SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
    id TEXT PRIMARY KEY, session_hash TEXT, question TEXT NOT NULL, alias TEXT NOT NULL,
    candidates TEXT NOT NULL, faq_key TEXT, revision TEXT, confidence REAL,
    official_answer TEXT, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS interaction_alias ON interactions(alias, faq_key, revision);
CREATE TABLE IF NOT EXISTS feedback (
    interaction_id TEXT PRIMARY KEY REFERENCES interactions(id),
    helpful INTEGER NOT NULL CHECK(helpful IN (0, 1)),
    updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS feedback_events (
    id INTEGER PRIMARY KEY, interaction_id TEXT NOT NULL REFERENCES interactions(id),
    helpful INTEGER NOT NULL CHECK(helpful IN (0, 1)), created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS promoted (
    alias TEXT NOT NULL, faq_key TEXT NOT NULL, revision TEXT NOT NULL, confidence REAL NOT NULL,
    official_answer TEXT NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(alias, faq_key, revision)
);
CREATE TABLE IF NOT EXISTS promotion_events (
    id INTEGER PRIMARY KEY, alias TEXT NOT NULL, faq_key TEXT NOT NULL, revision TEXT NOT NULL,
    action TEXT NOT NULL, evidence TEXT NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

DEFAULT_DB = Path(__file__).resolve().parents[3] / "data/processed/interactions.sqlite3"
MIN_CONFIDENCE = .84
MIN_SESSIONS = 3


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    path = Path(settings.learning_path) if settings.learning_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript(SCHEMA)
        with connection:
            yield connection
    finally:
        connection.close()


def session_hash(session: str | None) -> str | None:
    return hashlib.sha256(session.encode()).hexdigest() if session else None


def learned_scores(question: str, official: dict[str, FAQ]) -> dict[str, float]:
    if not settings.learning_enabled or redact(question) != question:
        return {}
    alias = normalize(question)
    words = tokens(question)
    scores: dict[str, float] = {}
    with database() as db:
        for row in db.execute("SELECT alias, faq_key, revision, confidence FROM promoted"):
            faq = official.get(row["faq_key"])
            if not faq or faq.revision != row["revision"]:
                continue
            if alias == row["alias"]:
                quality = 1.0
            else:
                similar = tokens(row["alias"])
                # Similar aliases only boost independent matches in the retriever.
                quality = .7 if len(words & similar) >= 4 and len(words & similar) / len(words | similar) >= .8 else 0
            if quality:
                scores[faq.key] = max(scores.get(faq.key, 0), quality * row["confidence"])
    return scores


def record(question: str, session: str | None, ranked: list[Match], chosen: Match | None) -> str | None:
    if not settings.learning_enabled:
        return None
    interaction_id = str(uuid4())
    safe_question = redact(question)
    # A question with recognizable identifiers stays in the audit ledger in redacted form.
    # It is ineligible for promotion.
    alias = normalize(question) if safe_question == question else ""
    eligible = chosen if chosen and chosen.faq.reviewed and alias else None
    candidates = [
        {"faq": item.faq.key, "revision": item.faq.revision, "score": round(item.score, 3), "method": item.method}
        for item in ranked[:settings.top_k]
    ]
    with database() as db:
        db.execute(
            """INSERT INTO interactions
            (id, session_hash, question, alias, candidates, faq_key, revision, confidence, official_answer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (interaction_id, session_hash(session), safe_question, alias, json.dumps(candidates),
             eligible.faq.key if eligible else None, eligible.faq.revision if eligible else None,
             eligible.score if eligible else None, eligible.faq.text if eligible else None),
        )
    return interaction_id if session else None


def rate(interaction: str, session: str, helpful: bool) -> bool:
    if not settings.learning_enabled:
        return False
    with database() as db:
        # Serialize the update and promotion across concurrent requests.
        db.execute("BEGIN IMMEDIATE")
        item = db.execute("SELECT * FROM interactions WHERE id=? AND session_hash=?",
                          (interaction, session_hash(session))).fetchone()
        if not item:
            return False
        current = db.execute("SELECT helpful FROM feedback WHERE interaction_id=?", (interaction,)).fetchone()
        if current and bool(current["helpful"]) == helpful:
            return True
        db.execute(
            """INSERT INTO feedback(interaction_id, helpful) VALUES (?, ?)
            ON CONFLICT(interaction_id) DO UPDATE SET helpful=excluded.helpful, updated=CURRENT_TIMESTAMP""",
            (interaction, int(helpful)),
        )
        db.execute("INSERT INTO feedback_events(interaction_id, helpful) VALUES (?, ?)", (interaction, int(helpful)))
        if item["faq_key"]:
            refresh_promotion(db, item)
    return True


def refresh_promotion(db: sqlite3.Connection, item: sqlite3.Row) -> None:
    key = item["alias"], item["faq_key"], item["revision"]
    rows = db.execute(
        """SELECT i.id, i.session_hash, f.helpful, i.confidence
        FROM interactions AS i JOIN feedback AS f ON f.interaction_id=i.id
        WHERE i.alias=? AND i.faq_key=? AND i.revision=?
        ORDER BY (SELECT MAX(e.id) FROM feedback_events AS e WHERE e.interaction_id=i.id) DESC""",
        key,
    )
    sessions: dict[str, sqlite3.Row] = {}
    for row in rows:
        sessions.setdefault(row["session_hash"], row)
    votes = list(sessions.values())
    positive = [v for v in votes if v["helpful"] and v["confidence"] >= MIN_CONFIDENCE]
    published = len(positive) >= MIN_SESSIONS and len(positive) / len(votes) >= .85
    old = db.execute("SELECT evidence FROM promoted WHERE alias=? AND faq_key=? AND revision=?", key).fetchone()
    evidence = json.dumps({"a_favor": [v["id"] for v in positive], "evaluadas": [v["id"] for v in votes]})
    if published:
        confidence = sum(v["confidence"] for v in positive) / len(positive)
        db.execute(
            """INSERT INTO promoted VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(alias, faq_key, revision) DO UPDATE SET confidence=excluded.confidence,
            official_answer=excluded.official_answer, evidence=excluded.evidence""",
            (*key, confidence, item["official_answer"], evidence),
        )
    elif old:
        db.execute("DELETE FROM promoted WHERE alias=? AND faq_key=? AND revision=?", key)
    if published != bool(old) or (published and old["evidence"] != evidence):
        action = "promovida" if published else "revocada"
        db.execute(
            "INSERT INTO promotion_events(alias, faq_key, revision, action, evidence) VALUES (?, ?, ?, ?, ?)",
            (*key, action, evidence),
        )
