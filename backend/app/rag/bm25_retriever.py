"""Lightweight BM25Okapi over the same chunk store FAISS uses.

No external dependency: the corpus is small (~10^2–10^3 chunks) so a pure-Python
implementation with per-query O(N) scoring is fine and avoids pulling rank-bm25.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from app.rag.vectorstore import Chunk

_TOKEN_RE = re.compile(r"[A-Za-z؀-ۿ][A-Za-z؀-ۿ\-']+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for",
    "is", "are", "was", "were", "be", "as", "by", "with", "from", "this",
    "that", "it", "its", "but", "not", "no", "if", "then", "than", "so",
    "we", "you", "he", "she", "they", "them", "his", "her", "our", "your",
    "do", "does", "did", "have", "has", "had", "can", "could", "may", "might",
    "patient", "patients", "disease", "diseases", "symptom", "symptoms",
}


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    toks = [t.lower() for t in _TOKEN_RE.findall(text)]
    return [t for t in toks if len(t) >= 2 and t not in _STOPWORDS]


@dataclass
class _DocStats:
    tf: dict[str, int]
    length: int


class BM25Index:
    """Standard BM25Okapi: idf(t) = ln((N - df + 0.5)/(df + 0.5) + 1)."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: list[_DocStats] = []
        self.df: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.avgdl: float = 0.0

    @classmethod
    def from_chunks(cls, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> "BM25Index":
        idx = cls(k1=k1, b=b)
        for c in chunks:
            idx._add(tokenize(c.text))
        idx._finalize()
        return idx

    def _add(self, tokens: list[str]) -> None:
        tf: dict[str, int] = {}
        for tok in tokens:
            tf[tok] = tf.get(tok, 0) + 1
        self.docs.append(_DocStats(tf=tf, length=len(tokens)))
        for tok in tf:
            self.df[tok] = self.df.get(tok, 0) + 1

    def _finalize(self) -> None:
        n = len(self.docs)
        self.avgdl = (sum(d.length for d in self.docs) / n) if n else 0.0
        self.idf = {
            t: math.log((n - df + 0.5) / (df + 0.5) + 1.0)
            for t, df in self.df.items()
        }

    def scores(self, query_tokens: list[str]) -> list[float]:
        out = [0.0] * len(self.docs)
        if not query_tokens or self.avgdl == 0:
            return out
        for q in query_tokens:
            idf = self.idf.get(q)
            if idf is None:
                continue
            for i, doc in enumerate(self.docs):
                tf = doc.tf.get(q, 0)
                if tf == 0:
                    continue
                norm = 1.0 - self.b + self.b * (doc.length / self.avgdl)
                out[i] += idf * (tf * (self.k1 + 1.0)) / (tf + self.k1 * norm)
        return out

    def search(self, query: str, k: int) -> list[tuple[int, float]]:
        scores = self.scores(tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda x: -x[1])
        return [(i, s) for i, s in ranked[:k] if s > 0.0]
