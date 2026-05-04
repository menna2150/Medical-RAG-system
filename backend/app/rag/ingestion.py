from __future__ import annotations

import json
import re
from pathlib import Path

from app.rag.vectorstore import Chunk

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _approx_token_count(text: str) -> int:
    return max(1, len(text.split()))


def _split_sentences(text: str) -> list[str]:
    # Light, dependency-free sentence splitter
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def chunk_text(text: str, target_tokens: int = 350, max_tokens: int = 500) -> list[str]:
    """Sentence-aware chunker. Targets 200–500 token windows."""
    sentences = _split_sentences(text)
    chunks: list[str] = []
    cur: list[str] = []
    cur_tok = 0
    for s in sentences:
        st = _approx_token_count(s)
        if cur_tok + st > max_tokens and cur:
            chunks.append(" ".join(cur))
            cur, cur_tok = [], 0
        cur.append(s)
        cur_tok += st
        if cur_tok >= target_tokens:
            chunks.append(" ".join(cur))
            cur, cur_tok = [], 0
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def build_corpus() -> list[Chunk]:
    """Build chunks from the curated disease corpus.

    Production: extend this function to ingest WHO ICD-11 (REST API), NICE PDFs,
    PubMed abstracts (E-utilities), and the EPFL clinical-guidelines HF dataset.
    Each ingested document becomes one or more Chunk(text, metadata).
    """
    diseases = json.loads((DATA_DIR / "diseases.json").read_text(encoding="utf-8"))
    symptom_map = json.loads((DATA_DIR / "symptom_mapping.json").read_text(encoding="utf-8"))

    sx_by_disease: dict[str, list[tuple[str, float]]] = {}
    for entry in symptom_map:
        sx_by_disease.setdefault(entry["disease_id"], []).append(
            (entry["symptom"], entry["weight"])
        )

    chunks: list[Chunk] = []
    next_id = 0
    for d in diseases:
        sxs = sx_by_disease.get(d["id"], [])
        sx_text = ", ".join(f"{s} (weight {w:.2f})" for s, w in sxs)

        document = (
            f"Disease: {d['name']} (ICD-11 {d.get('icd11','—')}).\n"
            f"Description: {d['description']}\n"
            f"Common presenting symptoms: {sx_text or ', '.join(d.get('symptoms', []))}.\n"
            f"Recommended diagnostic tests: {', '.join(d.get('tests', []))}.\n"
            f"Evidence-based treatments (generic names / classes): {', '.join(d.get('treatments', []))}.\n"
            f"Source: {d.get('source','curated')}."
        )
        for piece in chunk_text(document):
            chunks.append(
                Chunk(
                    id=next_id,
                    text=piece,
                    metadata={
                        "disease": d["name"],
                        "disease_id": d["id"],
                        "icd11": d.get("icd11"),
                        "symptoms": d.get("symptoms", []),
                        "tests": d.get("tests", []),
                        "treatments": d.get("treatments", []),
                        "source": d.get("source", "curated"),
                    },
                )
            )
            next_id += 1

    return chunks
