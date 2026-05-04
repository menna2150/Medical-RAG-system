from __future__ import annotations

import json
import logging
import re
from typing import AsyncIterator, Optional

from anthropic import AsyncAnthropic

from app.config import settings
from app.rag.vectorstore import Chunk

log = logging.getLogger("medrag.reasoner")

SYSTEM_PROMPT = """You are a medical decision-support assistant for licensed physicians in Egypt.

You produce a differential diagnosis, NOT a single final diagnosis. You never prescribe dosages.
You ground every claim in the provided clinical evidence chunks. If evidence is insufficient, say so
and return fewer (or zero) diagnoses rather than fabricating.

OUTPUT: a single JSON object, no prose, matching exactly this schema:
{
  "diagnoses": [
    {
      "name": "<disease name>",
      "icd11": "<ICD-11 code or null>",
      "reason": "<2-3 sentence clinical reasoning citing the evidence>",
      "tests": ["<recommended diagnostic test>", ...],
      "treatment_classes": ["<drug class or generic name>", ...],
      "source_ids": [<int chunk ids that support this diagnosis>]
    }
  ]
}

RULES:
- Return 3 to 5 diagnoses ranked from most to least likely. Fewer is fine if evidence is weak.
- treatment_classes MUST be generic names or drug classes only. NEVER brand names. NEVER dosages.
- source_ids must reference the chunk ids you actually used.
- If the symptoms do not match any retrieved evidence, return {"diagnoses": []}.
"""


def _format_chunks(chunks: list[tuple[Chunk, float]]) -> str:
    lines = []
    for c, score in chunks:
        meta = c.metadata
        lines.append(
            f"[chunk {c.id} | score={score:.3f} | disease={meta.get('disease','?')} | "
            f"source={meta.get('source','?')}]\n{c.text}"
        )
    return "\n\n".join(lines)


def _build_user_message(symptoms: str, age, gender, history, chunks) -> str:
    parts = [f"PATIENT PRESENTATION:\nSymptoms: {symptoms}"]
    if age is not None:
        parts.append(f"Age: {age}")
    if gender:
        parts.append(f"Gender: {gender}")
    if history:
        parts.append(f"Medical history: {history}")
    parts.append("\nRETRIEVED CLINICAL EVIDENCE:\n" + _format_chunks(chunks))
    parts.append("\nRespond with the JSON object only.")
    return "\n".join(parts)


def _extract_json(text: str) -> dict:
    # Models sometimes wrap JSON in fences. Be defensive.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        return json.loads(brace.group(0))
    raise ValueError("LLM did not return JSON")


async def reason_diagnoses(
    symptoms: str,
    age: Optional[int],
    gender: Optional[str],
    history: Optional[str],
    retrieved: list[tuple[Chunk, float]],
) -> list[dict]:
    if not settings.anthropic_api_key:
        log.warning("ANTHROPIC_API_KEY not set — returning evidence-only fallback")
        return _fallback_from_chunks(retrieved)

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    user_msg = _build_user_message(symptoms, age, gender, history, retrieved)

    try:
        resp = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = resp.content[0].text if resp.content else ""
        parsed = _extract_json(text)
        return parsed.get("diagnoses", [])
    except Exception as e:
        log.exception("LLM reasoning failed: %s", e)
        return _fallback_from_chunks(retrieved)


async def reason_diagnoses_stream(
    symptoms: str,
    age: Optional[int],
    gender: Optional[str],
    history: Optional[str],
    retrieved: list[tuple[Chunk, float]],
) -> AsyncIterator[tuple[str, object]]:
    """Stream Claude's reasoning. Yields ('delta', text_chunk) events as tokens arrive,
    then a final ('diagnoses', list[dict]) once parsing completes.

    On error or no API key, yields a single ('diagnoses', fallback) and no deltas."""
    if not settings.anthropic_api_key:
        log.warning("ANTHROPIC_API_KEY not set — streaming fallback")
        yield ("diagnoses", _fallback_from_chunks(retrieved))
        return

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    user_msg = _build_user_message(symptoms, age, gender, history, retrieved)

    buf: list[str] = []
    try:
        async with client.messages.stream(
            model=settings.anthropic_model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        ) as stream:
            async for text in stream.text_stream:
                buf.append(text)
                yield ("delta", text)
        full_text = "".join(buf)
        parsed = _extract_json(full_text)
        yield ("diagnoses", parsed.get("diagnoses", []))
    except Exception as e:
        log.exception("LLM streaming failed: %s", e)
        yield ("diagnoses", _fallback_from_chunks(retrieved))


def _fallback_from_chunks(retrieved: list[tuple[Chunk, float]]) -> list[dict]:
    """Deterministic fallback: group chunks by disease metadata and emit a stub diagnosis.
    Used when the LLM key is absent or the call fails — keeps the system useful in dev."""
    by_disease: dict[str, list[tuple[Chunk, float]]] = {}
    for chunk, score in retrieved:
        d = chunk.metadata.get("disease")
        if not d:
            continue
        by_disease.setdefault(d, []).append((chunk, score))

    out = []
    for disease, items in sorted(by_disease.items(), key=lambda kv: -max(s for _, s in kv[1]))[:5]:
        meta = items[0][0].metadata
        out.append({
            "name": disease,
            "icd11": meta.get("icd11"),
            "reason": (
                f"Evidence retrieved for {disease} with similarity up to "
                f"{max(s for _, s in items):.2f}. (LLM disabled: showing retrieval-only result.)"
            ),
            "tests": meta.get("tests", []),
            "treatment_classes": meta.get("treatments", []),
            "source_ids": [c.id for c, _ in items],
        })
    return out
