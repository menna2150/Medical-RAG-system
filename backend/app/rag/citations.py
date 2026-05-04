"""Compute which input symptom phrases drove each retrieved diagnosis.

Used by the frontend to highlight matched terms inline in the DiagnosisCard,
so the doctor can audit retrieval quality at a glance.
"""
from __future__ import annotations

import re

from app.rag.vectorstore import Chunk

# Split on commas, semicolons, "and", periods — the form's natural delimiters.
_INPUT_SPLIT = re.compile(r"\s*(?:,|;|\band\b|\.|\n)\s*", flags=re.IGNORECASE)
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-']+")


def _extract_phrases(symptoms: str) -> list[str]:
    """Split the free-text symptom field into phrases the doctor entered."""
    if not symptoms:
        return []
    raw = [p.strip() for p in _INPUT_SPLIT.split(symptoms)]
    return [p for p in raw if p and len(p) >= 3]


def _phrase_in_text(phrase: str, text: str) -> bool:
    """Case-insensitive substring or significant-word overlap.
    A phrase counts as matched if any of its content words (>=4 chars) appears in `text`."""
    if not phrase or not text:
        return False
    p_low = phrase.lower()
    t_low = text.lower()
    if p_low in t_low:
        return True
    for word in _WORD_RE.findall(p_low):
        if len(word) >= 4 and word in t_low:
            return True
    return False


def matched_symptoms(
    input_symptoms: str,
    supporting: list[tuple[Chunk, float]],
) -> list[str]:
    """Phrases from the doctor's input that appear in the supporting chunks
    (text or metadata.symptoms). Returns the original phrasing, deduplicated."""
    phrases = _extract_phrases(input_symptoms)
    if not phrases or not supporting:
        return []

    # Build the searchable haystack from each supporting chunk.
    haystack_parts: list[str] = []
    for chunk, _ in supporting:
        haystack_parts.append(chunk.text)
        meta_sx = chunk.metadata.get("symptoms") or []
        if isinstance(meta_sx, list):
            haystack_parts.extend(str(s) for s in meta_sx)
    haystack = " ".join(haystack_parts)

    seen: set[str] = set()
    out: list[str] = []
    for p in phrases:
        if p.lower() in seen:
            continue
        if _phrase_in_text(p, haystack):
            seen.add(p.lower())
            out.append(p)
    return out
