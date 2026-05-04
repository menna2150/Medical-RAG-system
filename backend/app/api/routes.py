import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.rag.query_processor import process_query
from app.rag.reasoner import reason_diagnoses, reason_diagnoses_stream
from app.rag.safety import postprocess

log = logging.getLogger("medrag.api")
router = APIRouter()

DISCLAIMER = (
    "This is a decision-support tool. Final decisions must be made by a licensed physician. "
    "Do not use as a substitute for clinical judgement, examination, or established protocols."
)


def _retrieve(request: Request, normalized) -> list:
    """Hybrid retrieval (dense + BM25 + RRF) followed by optional cross-encoder rerank."""
    embedder = request.app.state.embedder
    hybrid = request.app.state.hybrid
    reranker = getattr(request.app.state, "reranker", None)

    query_vec = embedder.encode([normalized.query_text])[0]
    pool_size = settings.rerank_pool if reranker else settings.top_k
    candidates = hybrid.retrieve(normalized.query_text, query_vec, k=pool_size)

    if reranker and len(candidates) > settings.top_k:
        candidates = reranker.rerank(normalized.query_text, candidates, top_k=settings.top_k)

    return candidates


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    drug_matcher = request.app.state.drug_matcher

    try:
        normalized = process_query(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    hits = _retrieve(request, normalized)

    if not hits:
        return AnalyzeResponse(
            diagnoses=[],
            disclaimer=DISCLAIMER,
            query_language=normalized.language,
            retrieval_quality=0.0,
        )

    raw_diagnoses = await reason_diagnoses(
        symptoms=normalized.query_text,
        age=req.age,
        gender=req.gender,
        history=req.history,
        retrieved=hits,
    )

    final = postprocess(raw_diagnoses, hits, drug_matcher, input_symptoms=req.symptoms)

    return AnalyzeResponse(
        diagnoses=final.diagnoses,
        disclaimer=DISCLAIMER,
        query_language=normalized.language,
        retrieval_quality=final.retrieval_quality,
    )


def _sse(event: str, data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/analyze/stream")
async def analyze_stream(req: AnalyzeRequest, request: Request):
    """Server-Sent Events: emits `retrieval`, `delta` (LLM tokens), `complete`, or `error`.

    Frontend renders the partial text as a 'thinking' indicator, then swaps in the
    parsed AnalyzeResponse on `complete`.
    """
    drug_matcher = request.app.state.drug_matcher

    try:
        normalized = process_query(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    async def event_stream():
        try:
            hits = _retrieve(request, normalized)

            yield _sse(
                "retrieval",
                {
                    "candidates": len(hits),
                    "language": normalized.language,
                    "top_score": round(float(hits[0][1]), 3) if hits else 0.0,
                },
            )

            if not hits:
                yield _sse(
                    "complete",
                    {
                        "diagnoses": [],
                        "disclaimer": DISCLAIMER,
                        "query_language": normalized.language,
                        "retrieval_quality": 0.0,
                    },
                )
                return

            raw_diagnoses: list[dict] = []
            async for kind, payload in reason_diagnoses_stream(
                symptoms=normalized.query_text,
                age=req.age,
                gender=req.gender,
                history=req.history,
                retrieved=hits,
            ):
                if kind == "delta":
                    yield _sse("delta", {"text": payload})
                elif kind == "diagnoses":
                    raw_diagnoses = payload  # type: ignore[assignment]

            final = postprocess(
                raw_diagnoses, hits, drug_matcher, input_symptoms=req.symptoms
            )

            yield _sse(
                "complete",
                {
                    "diagnoses": [d.model_dump() for d in final.diagnoses],
                    "disclaimer": DISCLAIMER,
                    "query_language": normalized.language,
                    "retrieval_quality": final.retrieval_quality,
                },
            )
        except Exception as e:
            log.exception("stream failed: %s", e)
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
