import os

import chromadb
from sentence_transformers import SentenceTransformer

from app.config import settings

_model: SentenceTransformer | None = None
_client = None
_collection = None


def embed(texts: list[str]) -> list[list[float]]:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model.encode(texts, normalize_embeddings=True).tolist()


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        os.makedirs(settings.chroma_path, exist_ok=True)
        _client = chromadb.PersistentClient(path=settings.chroma_path)
    return _client


def get_collection():
    global _collection
    if _collection is None:
        _collection = get_client().get_or_create_collection(
            name="faq_penalolen", metadata={"hnsw:space": "cosine"}
        )
    return _collection
