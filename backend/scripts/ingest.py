
"""Build the optional semantic index from the same snapshot served by the API."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings
from app.services.knowledge import is_active  # re-exported for the original ingestion checks
from app.services.rag import get_index
from app.services.vector_store import embed, get_client, snapshot_name


def main() -> None:
    engine = get_index()
    faqs = list(engine.faqs.values())
    if not faqs:
        raise ValueError("La base no contiene fichas utilizables")
    name = snapshot_name(engine.revision)
    documents = [f"{faq.question}\n{faq.tags}\n{faq.category}" for faq in faqs]
    vectors = embed(documents)
    client = get_client()
    collection = client.get_or_create_collection(name=name, metadata={
        "hnsw:space": "cosine", "embedding_model": settings.embedding_model,
        "faq_revision": engine.revision,
    })
    collection.upsert(
        ids=[faq.key for faq in faqs], documents=documents, embeddings=vectors,
        metadatas=[faq.source() for faq in faqs],
    )
    print(f"Indexadas {collection.count()} fichas en {settings.chroma_path} ({name})")


if __name__ == "__main__":
    main()
