from __future__ import annotations

import numpy as np

from app.rag.vectorstore import Chunk, VectorStore


def retrieve(store: VectorStore, query_vec: np.ndarray, k: int = 8, mmr_lambda: float = 0.7) -> list[tuple[Chunk, float]]:
    """Top-k retrieval with MMR re-ranking for diversity.

    MMR (Maximal Marginal Relevance) reduces near-duplicate chunks that all describe the same disease;
    we want the LLM to see *different* candidate diagnoses.
    """
    candidates = store.search(query_vec, k * 3)
    if not candidates:
        return []

    selected: list[tuple[Chunk, float]] = []
    cand_list = list(candidates)

    # First pick is highest scoring
    selected.append(cand_list.pop(0))

    while cand_list and len(selected) < k:
        best_idx = -1
        best_score = -1e9
        for i, (chunk, score) in enumerate(cand_list):
            penalty = 0.0
            for s_chunk, _ in selected:
                if chunk.metadata.get("disease") == s_chunk.metadata.get("disease"):
                    penalty = max(penalty, 0.6)
            mmr = mmr_lambda * score - (1 - mmr_lambda) * penalty
            if mmr > best_score:
                best_score = mmr
                best_idx = i
        if best_idx == -1:
            break
        selected.append(cand_list.pop(best_idx))

    return selected
