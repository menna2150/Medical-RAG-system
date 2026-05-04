import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.rag.bm25_retriever import BM25Index
from app.rag.embeddings import Embedder
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.reranker import Reranker
from app.rag.vectorstore import VectorStore
from app.rag.drug_matcher import DrugMatcher

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("medrag")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading embedder: %s", settings.embedding_model)
    app.state.embedder = Embedder(settings.embedding_model)

    log.info("Loading FAISS index from %s", settings.index_path)
    app.state.vectorstore = VectorStore.load(settings.index_path)

    log.info("Building BM25 index over %d chunks", len(app.state.vectorstore.chunks))
    app.state.bm25 = BM25Index.from_chunks(app.state.vectorstore.chunks)

    app.state.hybrid = HybridRetriever(
        store=app.state.vectorstore,
        bm25=app.state.bm25,
        fanout=settings.retrieve_fanout,
        rrf_k=settings.rrf_k,
    )

    if settings.cross_encoder_model:
        try:
            app.state.reranker = Reranker(settings.cross_encoder_model)
        except Exception as e:
            log.warning("Cross-encoder failed to load (%s) — running without reranker", e)
            app.state.reranker = None
    else:
        app.state.reranker = None

    log.info("Loading Egyptian drug DB")
    app.state.drug_matcher = DrugMatcher.from_default()

    log.info("Startup complete")
    yield


app = FastAPI(
    title="MedRAG-EG",
    description=(
        "Medical decision-support RAG system for licensed physicians in Egypt. "
        "This is a decision-support tool. Final decisions must be made by a licensed physician."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
