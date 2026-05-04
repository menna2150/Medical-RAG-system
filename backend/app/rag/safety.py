from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from app.config import settings
from app.rag.citations import matched_symptoms
from app.rag.drug_matcher import DrugMatcher
from app.rag.vectorstore import Chunk
from app.schemas import Confidence, Diagnosis, Treatment


@dataclass
class PostprocessResult:
    diagnoses: list[Diagnosis]
    retrieval_quality: float


def _score_to_confidence(score: float) -> Confidence:
    if score >= 0.65:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _supporting_chunks(source_ids: list[int], hits: list[tuple[Chunk, float]]) -> list[tuple[Chunk, float]]:
    by_id = {c.id: (c, s) for c, s in hits}
    return [by_id[i] for i in source_ids if i in by_id]


def _confidence_score(supporting: list[tuple[Chunk, float]], all_hits: list[tuple[Chunk, float]]) -> float:
    """Confidence = mean similarity of supporting chunks, slightly boosted by agreement
    (multiple chunks supporting the same diagnosis). Clamped to [0,1]."""
    if not supporting:
        # Fall back to mean of top hit
        return max(0.0, min(1.0, all_hits[0][1] if all_hits else 0.0))
    base = mean(s for _, s in supporting)
    agreement_bonus = min(0.1, 0.03 * (len(supporting) - 1))
    return max(0.0, min(1.0, base + agreement_bonus))


def _resolve_treatments(treatment_terms: list[str], matcher: DrugMatcher) -> list[Treatment]:
    """Drop anything not in the curated EG drug DB. Deduplicate by generic name."""
    seen: set[str] = set()
    out: list[Treatment] = []
    for t in treatment_terms or []:
        for tr in matcher.resolve(t):
            if tr.drug.lower() in seen:
                continue
            seen.add(tr.drug.lower())
            out.append(tr)
    return out


def postprocess(
    raw_diagnoses: list[dict],
    hits: list[tuple[Chunk, float]],
    matcher: DrugMatcher,
    input_symptoms: str = "",
) -> PostprocessResult:
    retrieval_quality = float(mean(s for _, s in hits)) if hits else 0.0

    final: list[Diagnosis] = []
    for d in raw_diagnoses:
        supporting = _supporting_chunks(d.get("source_ids", []), hits)
        score = _confidence_score(supporting, hits)
        if score < settings.min_retrieval_score:
            continue

        sources = list({
            c.metadata.get("source", "unknown")
            for c, _ in supporting
        })

        treatments = _resolve_treatments(d.get("treatment_classes", []), matcher)
        matched = matched_symptoms(input_symptoms, supporting)

        final.append(
            Diagnosis(
                name=d["name"],
                icd11=d.get("icd11"),
                confidence=_score_to_confidence(score),
                confidence_score=round(score, 3),
                reason=d.get("reason", ""),
                tests=d.get("tests", []),
                treatments=treatments,
                sources=sources,
                matched_symptoms=matched,
            )
        )

    final.sort(key=lambda x: x.confidence_score, reverse=True)
    return PostprocessResult(diagnoses=final[:5], retrieval_quality=round(retrieval_quality, 3))
