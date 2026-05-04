# MedRAG-EG · Architecture & Pipeline

## 1. Top-level architecture

```
[Doctor's browser]
       │  HTTPS
       ▼
[ React (Vite) ]  ───▶  POST /analyze  ───▶  [ FastAPI ]
                                                 │
                                                 ▼
                       ┌─────────────────────────────────────┐
                       │  Query processor (EN/AR norm)        │
                       │  Embedder (S-BioBERT)                │
                       │  FAISS retriever (top-k + MMR)       │
                       │  LLM reasoner (Claude, grounded)     │
                       │  Drug matcher (curated EG DB)        │
                       │  Safety / scorer / disclaimer        │
                       └────────────────┬────────────────────┘
                                        ▼
                                Validated JSON
```

## 2. Step-by-step pipeline (one analyze request)

| # | Stage | Module | Output |
|---|-------|--------|--------|
| 1 | Parse request | `schemas.AnalyzeRequest` | typed request |
| 2 | Detect language, normalize AR symptoms, enrich with age/gender/history | `rag.query_processor` | `NormalizedQuery` |
| 3 | Embed the query | `rag.embeddings.Embedder` | 768-d vector |
| 4 | Top-k FAISS search + MMR re-rank | `rag.retriever.retrieve` | list of (chunk, score) |
| 5 | Build grounded prompt, call Claude → strict JSON dx list | `rag.reasoner` | raw `[{name,reason,tests,treatment_classes,source_ids}, ...]` |
| 6 | Look up each `treatment_class` in the curated Egyptian drug DB; drop unresolved drugs | `rag.drug_matcher` | resolved Treatments |
| 7 | Compute confidence (mean similarity of supporting chunks + agreement bonus); drop diagnoses below floor; sort | `rag.safety` | `Diagnosis[]` |
| 8 | Attach disclaimer + retrieval quality | `api.routes` | `AnalyzeResponse` |

## 3. Data flow & schema

- **Knowledge corpus** → `backend/app/data/diseases.json`
  → ingested into FAISS chunks at index-build time.
- **Symptom→disease weights** → `backend/app/data/symptom_mapping.json`
  → woven into chunk text so retrieval surfaces them.
- **Egyptian drugs** → `backend/app/data/medications_egypt.json`
  → loaded by `DrugMatcher` at startup, used at request time.

The relational target schema is in `backend/app/db/schema.sql`.

## 4. Tech-stack rationale

- **S-BioBERT** for embeddings: domain-specific biomedical sentence embeddings beat general-purpose models on symptom & disease vocabulary; the model is ~110M params and runs comfortably on CPU.
- **FAISS** (`IndexFlatIP` on normalized vectors): zero-ops, file-based, easy to bake into a Docker image. Pluggable to `IndexHNSWFlat` once the corpus exceeds ~100k chunks, and pluggable to Pinecone for multi-tenant scale.
- **FastAPI**: async, OpenAPI out of the box, Pydantic ensures the strict response contract.
- **Claude (Sonnet 4.6 / Opus 4.7)**: strong instruction-following, JSON-mode-friendly via system prompt, and well-suited for grounded reasoning when chunks are provided.
- **React + Vite + Tailwind**: fastest iteration loop, easy to deploy as static assets behind any CDN.

## 5. Safety guarantees

- **No invented drugs**: drugs are pulled only from `medications_egypt.json`; anything else the LLM proposes is dropped silently.
- **No final diagnoses**: API contract requires up to 5 ranked candidates; UI labels them "Differential diagnoses".
- **No dosages**: removed from the LLM contract (only generic name + brand + price range).
- **Confidence is data-driven**: computed from retrieval similarity, not LLM self-assessment.
- **Hard floor**: diagnoses below `MIN_RETRIEVAL_SCORE` are dropped — empty result is preferred to a low-confidence guess.
- **Always-on disclaimer** at the API and UI layers.

## 6. Deployment plan

### Dev (local)
```
backend  : uvicorn app.main:app --reload --port 8000
frontend : npm run dev   # 5173
```

### Production
- `docker compose up -d --build` brings up backend (Uvicorn) and frontend (Nginx serving the built React app).
- Set `ANTHROPIC_API_KEY` and `ALLOWED_ORIGINS` in env. Restrict CORS to the actual web origin.
- Behind a reverse proxy (Nginx / Cloudflare) with HTTPS.
- The FAISS index is built into the backend image. To refresh:
  1. Update `backend/app/data/*.json`.
  2. `docker compose build backend && docker compose up -d backend`.
  3. Or run `python -m app.scripts.build_index` against a mounted volume.
- Egyptian drug prices: each entry has `last_verified`. Schedule a quarterly re-validation against EDA / Dawaey.

### Observability
- `/health` for liveness.
- Add structured request logs (already wired through `logging`).
- For audit, persist `(request, retrieved_chunks, llm_output, final_response)` to a write-once log if regulatory requirements demand it.

## 7. Component map

```
backend/
├── app/
│   ├── main.py                FastAPI app + lifespan
│   ├── config.py              env-driven settings
│   ├── schemas.py             API contract
│   ├── api/routes.py          POST /analyze
│   ├── rag/
│   │   ├── ingestion.py       chunker + corpus builder
│   │   ├── embeddings.py      S-BioBERT wrapper
│   │   ├── vectorstore.py     FAISS persistence
│   │   ├── query_processor.py EN/AR normalizer
│   │   ├── retriever.py       top-k + MMR
│   │   ├── reasoner.py        grounded LLM call
│   │   ├── drug_matcher.py    EG-market lookup
│   │   └── safety.py          confidence + filter
│   ├── db/schema.sql          target relational schema
│   ├── data/                  curated JSON (diseases / symptoms / drugs)
│   └── scripts/build_index.py FAISS builder
└── Dockerfile

frontend/
├── src/
│   ├── App.jsx                shell + state
│   ├── api.js                 Axios client
│   ├── i18n.js                EN / AR strings
│   └── components/
│       ├── Header.jsx
│       ├── Disclaimer.jsx
│       ├── SymptomForm.jsx    text + voice input
│       ├── DiagnosisCard.jsx  collapsible card
│       ├── MedicationTable.jsx
│       ├── SavedCases.jsx     localStorage history
│       ├── Loader.jsx         spinner + skeleton
│       └── ErrorMessage.jsx
└── Dockerfile + nginx.conf
```
