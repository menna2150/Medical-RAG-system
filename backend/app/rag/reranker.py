"""Cross-encoder reranker. Pairwise (query, chunk) scoring on the top-N candidates
from hybrid retrieval, then keep top-k for the LLM.

Cross-encoders attend over both texts jointly, so they catch nuanced matches a
bi-encoder (S-BioBERT) misses — at the cost of one forward pass per (query, doc)
pair. We only run it on the candidate pool (~20 docs), so latency stays sub-second
on CPU with the small MiniLM cross-encoder.
"""
from __future__ import annotations

import logging

from app.rag.vectorstore import Chunk

log = logging.getLogger("medrag.reranker")


class Reranker:
    def __init__(self, model_name: str):
        # Lazy import so a bad model name doesn't crash startup
        from sentence_transformers import CrossEncoder
        log.info("Loading cross-encoder: %s", model_name)
        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        candidates: list[tuple[Chunk, float]],
        top_k: int,
    ) -> list[tuple[Chunk, float]]:
        if not candidates:
            return []
        pairs = [(query, c.text) for c, _ in candidates]
        try:
            ce_scores = self.model.predict(pairs, show_progress_bar=False)
        except Exception as e:
            log.warning("Cross-encoder predict failed (%s) — returning input order", e)
            return candidates[:top_k]

        # Combine: keep the original (dense) score for downstream confidence math,
        # but order by cross-encoder score.
        scored = list(zip(candidates, ce_scores))
        scored.sort(key=lambda x: -float(x[1]))
        return [c for c, _ in scored[:top_k]]
