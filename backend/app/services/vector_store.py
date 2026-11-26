
import hashlib
from pathlib import Path

from app.config import settings

_model = None
_client = None


def embed(texts: list[str]) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer

    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model.encode(texts, normalize_embeddings=True).tolist()


def get_client():
    import chromadb

    global _client
    if _client is None:
        path = Path(settings.chroma_path)
        path.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(path))
    return _client


def snapshot_name(revision: str) -> str:
    key = hashlib.sha256(f"{revision}:{settings.embedding_model}".encode()).hexdigest()[:20]
    return f"faq_penalolen_{key}"


def get_collection(revision: str):
    return get_client().get_collection(name=snapshot_name(revision))
