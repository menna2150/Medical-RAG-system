"""Hybrid retrieval: dense (FAISS) + lexical (BM25) fused with Reciprocal Rank Fusion.

Why hybrid: S-BioBERT alone misses rare-disease keyword matches (e.g., "schistosomiasis",
"brucellosis") whose embeddings are noisy in general-purpose biomedical models. BM25 catches
exact term hits; dense catches paraphrase. RRF combines them with no score-scale calibration.
"""
from __future__ import annotations

import numpy as np

from app.rag.bm25_retriever import BM25Index
from app.rag.vectorstore import Chunk, VectorStore


def _rrf_fuse(
    rankings: list[list[int]],
    k: int = 60,
) -> dict[int, float]:
    """Reciprocal Rank Fusion. Each ranked list contributes 1/(k + rank) to each doc."""
    out: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            out[doc_id] = out.get(doc_id, 0.0) + 1.0 / (k + rank)
    return out


def _mmr_dedupe(
    candidates: list[tuple[Chunk, float]],
    k: int,
    lam: float = 0.7,
) -> list[tuple[Chunk, float]]:
    """Same MMR-style dedup as the original retriever: penalize chunks from a disease
    we have already selected, so the LLM sees diverse candidates."""
    if not candidates:
        return []
    selected: list[tuple[Chunk, float]] = [candidates[0]]
    pool = candidates[1:]
    while pool and len(selected) < k:
        best_idx, best_score = -1, -1e9
        for i, (chunk, score) in enumerate(pool):
            penalty = 0.0
            for s_chunk, _ in selected:
                if chunk.metadata.get("disease") == s_chunk.metadata.get("disease"):
                    penalty = max(penalty, 0.6)
            mmr = lam * score - (1 - lam) * penalty
            if mmr > best_score:
                best_score, best_idx = mmr, i
        if best_idx == -1:
            break
        selected.append(pool.pop(best_idx))
    return selected


class HybridRetriever:
    def __init__(self, store: VectorStore, bm25: BM25Index, fanout: int = 30, rrf_k: int = 60):
        self.store = store
        self.bm25 = bm25
        self.fanout = fanout
        self.rrf_k = rrf_k

    def retrieve(
        self,
        query_text: str,
        query_vec: np.ndarray,
        k: int = 8,
    ) -> list[tuple[Chunk, float]]:
        # Dense — keep the IP score for downstream confidence calculation
        dense_hits = self.store.search(query_vec, self.fanout)
        dense_scores = {c.id: s for c, s in dense_hits}
        dense_rank = [c.id for c, _ in dense_hits]

        # Lexical
        bm25_hits = self.bm25.search(query_text, self.fanout)
        bm25_rank = [self.store.chunks[i].id for i, _ in bm25_hits if 0 <= i < len(self.store.chunks)]

        # RRF
        fused = _rrf_fuse([dense_rank, bm25_rank], k=self.rrf_k)
        if not fused:
            return []

        # Order by RRF, but expose dense similarity as the score so confidence math
        # stays calibrated. For docs only retrieved by BM25, use 0 (postprocess clamps).
        by_id = {c.id: c for c in self.store.chunks}
        ordered = sorted(fused.items(), key=lambda kv: -kv[1])
        candidates: list[tuple[Chunk, float]] = []
        for doc_id, _rrf_score in ordered:
            chunk = by_id.get(doc_id)
            if chunk is None:
                continue
            candidates.append((chunk, float(dense_scores.get(doc_id, 0.0))))

        # Dedup-by-disease to give the LLM diverse candidates
        return _mmr_dedupe(candidates, k=k)
