# MedRAG-EG — Medical Decision-Support RAG System for Egyptian Doctors

> ⚠️ **Decision support only.** Final diagnoses and prescriptions must be made by a licensed physician.

A production-ready Retrieval-Augmented Generation (RAG) system that takes patient symptoms and returns ranked differential diagnoses with evidence, recommended tests, treatments, and **medications available in the Egyptian market** (with EGP price ranges).

---

## 1. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          REACT FRONTEND (Vite + Tailwind)              │
│   SymptomForm  →  /analyze  →  DiagnosisCards + MedicationTable        │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │ HTTPS / Axios
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       FASTAPI  BACKEND (Python 3.11)                   │
│                                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────────────┐  │
│  │ Query Proc.  │ →  │ Embedding    │ →  │ FAISS Vector Retrieval  │  │
│  │ (EN/AR norm) │    │ (BioBERT)    │    │ (top-k chunks)          │  │
│  └──────────────┘    └──────────────┘    └────────────┬────────────┘  │
│                                                        │                │
│  ┌──────────────────────────────────────────────────────▼────────────┐ │
│  │ Reasoner (LLM)  -- grounded prompt with retrieved evidence         │ │
│  │   → Differential dx (top 3–5) with confidence + reasoning          │ │
│  └────────────┬───────────────────────────────────────────────────────┘ │
│               ▼                                                         │
│  ┌──────────────────────┐    ┌──────────────────────────────────────┐  │
│  │ Drug Matcher (EG)    │ →  │ Safety / Post-processing             │  │
│  │ generic→brand+price  │    │ confidence floor + disclaimer + filter│  │
│  └──────────────────────┘    └────────────┬─────────────────────────┘  │
│                                           ▼                            │
│                                    Validated JSON                      │
└────────────────────────────────────────────────────────────────────────┘
                               ▲
                               │ Index built offline
┌──────────────────────────────┴─────────────────────────────────────────┐
│  INGESTION  — WHO ICD-11, NICE, PubMed, EPFL guidelines, EDA drugs    │
│   clean → chunk(200–500 tok) → metadata(disease, symptoms, source)    │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Pipeline (step-by-step)

1. **Ingestion** — pull from WHO ICD-11 API, EPFL clinical-guidelines corpus, PubMed E-utilities, scraped EDA drug list. Clean → chunk (200–500 tokens, sentence-aware) → tag metadata `{disease, symptoms[], source, evidence_level}`.
2. **Embedding** — `pritamdeka/S-BioBert-snli-multinli-stsb` (Sentence-BioBERT). Domain-specific = better recall on medical terminology than general-purpose models.
3. **Index** — FAISS `IndexFlatIP` with normalized vectors (cosine similarity). Persisted to disk.
4. **Query processing** — language detection (EN/AR), Arabic→English symptom normalization via a curated lexicon, embedding.
5. **Retrieval** — top-k (k=8) with metadata filters; MMR re-ranking to reduce redundancy.
6. **Reasoning** — grounded LLM prompt: "Given ONLY these chunks…produce 3–5 differential diagnoses." Refuses to answer if retrieval scores are too low.
7. **Drug matching** — for each diagnosis, look up structured `medications_egypt.json` (generic → brands → EGP range). Never invented by the LLM.
8. **Safety** — confidence is computed from retrieval similarity + agreement across chunks, not LLM self-report. Disclaimer always attached. Drugs not in the EG DB are dropped.
9. **Output** — strict JSON schema validated with Pydantic.

## 3. Tech-stack justification

| Layer | Choice | Why |
|---|---|---|
| LLM | Anthropic Claude (configurable) | Strong instruction-following, low hallucination on grounded prompts |
| Embeddings | S-BioBERT | Trained on biomedical corpora; best recall for symptom/disease vocab |
| Vector DB | FAISS | Free, fast, zero-ops, file-based — perfect for a single-tenant deployment. Pluggable to Pinecone if scale demands. |
| Backend | FastAPI | Async, Pydantic validation aligns with the strict JSON contract |
| Frontend | React + Vite + Tailwind | Fast dev loop, modern UX, easy to deploy as static site |
| Lang | EN + AR | Egyptian doctors mix Arabic patient narratives with English clinical terms |

## 4. Data sources

- **Knowledge** — WHO ICD-11 REST API, EPFL clinical-guidelines corpus (HF), PubMed E-utilities (NLM)
- **Symptom→disease** — Disease-Symptom CSV (133 dx × 132 sx), Human symptom–disease network (TF-IDF > 3.5)
- **Egyptian drugs** — EDDB (registration), Kaggle scraped EDA dataset (prices), Dawaey.com (live lookup)

> Always date-check prices: EDA approved 25–30% increases on antibiotics & chronic-disease meds in 2024.

## 5. Running locally

### Backend
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # add ANTHROPIC_API_KEY
python -m app.scripts.build_index   # builds FAISS from sample data
uvicorn app.main:app --reload --port 8000
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

Frontend on http://localhost:5173, backend on http://localhost:8000, docs at /docs.

## 6. Deployment

- **Backend**: Dockerized FastAPI behind Nginx; FAISS index baked into image or mounted volume; deploy on Fly.io / Railway / a small VM. Health check at `/health`.
- **Frontend**: `npm run build` → static files on Netlify / Vercel / Cloudflare Pages. Set `VITE_API_URL` to backend URL.
- **Index rebuild**: nightly cron in `scripts/build_index.py`. Drug prices flagged with `last_verified` date.
- **Secrets**: `ANTHROPIC_API_KEY`, no other PII stored. CORS locked to known frontend origins.

## 7. Constraints honored

- Never returns a single "final diagnosis" — always 3–5 ranked possibilities
- Never returns dosages — only generic name, brands, price range
- Drugs are pulled from a curated DB, never generated
- Disclaimer present on every response and every UI screen

See `backend/app/` and `frontend/src/` for the code.
