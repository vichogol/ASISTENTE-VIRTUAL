import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings
from app.services.vector_store import embed, get_client, get_collection

EXCEL = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "raw", "preguntas_frecuentes_penalolen.xlsx"
)


def is_active(v) -> bool:
    if pd.isna(v):
        return True
    try:
        return float(v) == 1.0
    except (ValueError, TypeError):
        return True


def main() -> None:
    df = pd.read_excel(EXCEL)
    df = df[df["isActivo"].apply(is_active)].copy()

    ids, docs, metas = [], [], []
    for _, r in df.iterrows():
        q = str(r["nombrePreguntaFrecuente"]).strip()
        desc = str(r["descripcionPreguntaFrecuente"]).strip()
        cat = str(r["categoriaPreguntaFrecuente"]).strip()
        direccion = str(r["Direccion"]).strip()
        tags = str(r["tagPreguntaFrecuente"]).strip() if pd.notna(r["tagPreguntaFrecuente"]) else ""
        texto = (
            f"Pregunta: {q}\nRespuesta: {desc}\nCategoría: {cat}\n"
            f"Dependencia: {direccion}\nTags: {tags}"
        )
        ids.append(str(r["preguntaFrecuenteID"]))
        docs.append(texto)
        metas.append(
            {
                "id": int(r["preguntaFrecuenteID"]),
                "pregunta": q,
                "categoria": cat,
                "direccion": direccion,
                "rango_etareo": (
                    str(r["Rango Etáreo"]).strip() if pd.notna(r["Rango Etáreo"]) else "general"
                ),
                "sexo": str(r["Sexo"]).strip() if pd.notna(r["Sexo"]) else "general",
            }
        )

    client = get_client()
    try:
        client.delete_collection("faq_penalolen")
    except Exception:
        pass
    coll = client.create_collection(name="faq_penalolen", metadata={"hnsw:space": "cosine"})

    # reset cached handle
    import app.services.vector_store as vs

    vs._collection = coll

    embs = embed(docs)
    coll.add(ids=ids, documents=docs, embeddings=embs, metadatas=metas)
    print(f"Ingestadas {len(ids)} preguntas en {settings.chroma_path}")


if __name__ == "__main__":
    main()
