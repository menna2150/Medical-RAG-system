from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np


@dataclass
class Chunk:
    id: int
    text: str
    metadata: dict


class VectorStore:
    """FAISS index + parallel chunk store. Inner-product on normalized vectors."""

    def __init__(self, index: faiss.Index, chunks: list[Chunk]):
        self.index = index
        self.chunks = chunks

    @classmethod
    def build(cls, vectors: np.ndarray, chunks: list[Chunk]) -> "VectorStore":
        if vectors.dtype != np.float32:
            vectors = vectors.astype("float32")
        dim = vectors.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(vectors)
        return cls(index, chunks)

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path / "faiss.index"))
        with (path / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for c in self.chunks:
                f.write(json.dumps({"id": c.id, "text": c.text, "metadata": c.metadata}) + "\n")

    @classmethod
    def load(cls, path: Path) -> "VectorStore":
        index_file = path / "faiss.index"
        chunks_file = path / "chunks.jsonl"
        if not index_file.exists() or not chunks_file.exists():
            raise FileNotFoundError(
                f"Index missing at {path}. Run `python -m app.scripts.build_index` first."
            )
        index = faiss.read_index(str(index_file))
        chunks = []
        with chunks_file.open(encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                chunks.append(Chunk(id=d["id"], text=d["text"], metadata=d["metadata"]))
        return cls(index, chunks)

    def search(self, query: np.ndarray, k: int) -> list[tuple[Chunk, float]]:
        if query.ndim == 1:
            query = query.reshape(1, -1)
        if query.dtype != np.float32:
            query = query.astype("float32")
        scores, ids = self.index.search(query, k)
        out: list[tuple[Chunk, float]] = []
        for idx, score in zip(ids[0], scores[0]):
            if idx < 0:
                continue
            out.append((self.chunks[idx], float(score)))
        return out
