"""Build the FAISS index from the curated corpus.

Run from `backend/`:

    python -m app.scripts.build_index
"""
from __future__ import annotations

import logging
import sys

from app.config import settings
from app.rag.embeddings import Embedder
from app.rag.ingestion import build_corpus
from app.rag.vectorstore import VectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("build_index")


def main() -> int:
    log.info("Building corpus...")
    chunks = build_corpus()
    log.info("Chunks: %d", len(chunks))

    log.info("Loading embedder: %s", settings.embedding_model)
    embedder = Embedder(settings.embedding_model)

    log.info("Encoding...")
    vectors = embedder.encode([c.text for c in chunks])
    log.info("Vectors: %s", vectors.shape)

    store = VectorStore.build(vectors, chunks)
    settings.index_path.mkdir(parents=True, exist_ok=True)
    store.save(settings.index_path)
    log.info("Saved index to %s", settings.index_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
