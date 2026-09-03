# mini-rag

A minimal, from-scratch **Retrieval-Augmented Generation** application, built step by step as a
teaching project. The goal is not to wrap a framework in three lines — it is to build each moving
part of a RAG pipeline (ingest → chunk → embed → index → retrieve → generate) explicitly, so the
tradeoffs at every stage are visible.

> **Status:** scaffold. The project layout, Python version and dependency set are pinned; the
> application code is built up over the tutorial steps below.

---

## What you build

```
        ┌──────────────┐   upload    ┌───────────────┐   enqueue   ┌──────────────┐
        │   Client     │ ──────────► │   FastAPI     │ ──────────► │    Celery    │
        └──────────────┘             │   (asgi)      │             │   workers    │
               ▲                     └───────┬───────┘             └──────┬───────┘
               │  answer + sources           │                            │
               │                             │ query                      │ parse (PyMuPDF)
               │                             ▼                            │ chunk
        ┌──────┴───────┐             ┌───────────────┐                    │ embed
        │     LLM      │ ◄────────── │  Retriever    │                    ▼
        │ OpenAI/Cohere│   context   │  (top-k)      │ ◄──────── ┌──────────────────┐
        └──────────────┘             └───────────────┘  vectors  │  Qdrant / pgvector│
                                                                 └──────────────────┘
                    MongoDB: documents & chunks     Redis: broker + result backend
```

A request lifecycle:

1. **Ingest** — a file is uploaded to the API and handed to a Celery task, so a 200 MB PDF never
   blocks the event loop.
2. **Parse & chunk** — PyMuPDF extracts text; the text is split into overlapping chunks sized for
   the embedding model's context.
3. **Embed & index** — each chunk is embedded and written to the vector store alongside its
   metadata (source document, page, position).
4. **Retrieve** — a user question is embedded with the *same* model and used for a top-k
   similarity search.
5. **Generate** — the retrieved chunks are assembled into a prompt with an explicit instruction to
   answer only from the supplied context, and the answer is returned with its sources.

## Stack

| Concern | Choice |
| --- | --- |
| API | FastAPI + Uvicorn |
| Background work | Celery + Redis (Flower for inspection) |
| Document / chunk store | MongoDB (Motor, `pydantic-mongo`) |
| Relational store | PostgreSQL (SQLAlchemy 2.0, Alembic, asyncpg) |
| Vector store | Qdrant, or `pgvector` in the same Postgres |
| Embeddings & generation | OpenAI or Cohere, behind one provider interface |
| Parsing & splitting | PyMuPDF, NLTK, LangChain text splitters |
| Observability | `prometheus-client` + `starlette-exporter`, `fastapi-health` |

Both vector backends are covered on purpose: Qdrant shows a purpose-built vector database, pgvector
shows how far one Postgres instance gets you before you need one.

## Requirements

- Python 3.12 (see [.python-version](.python-version))
- [uv](https://docs.astral.sh/uv/) for dependency management
- Docker, for the backing services
- An API key for OpenAI and/or Cohere

## Getting started

```bash
git clone <your-fork-url> mini-rag
cd mini-rag

# Creates .venv and installs the exact pinned versions from uv.lock
uv sync

# Sanity check
uv run rag
# Hello from rag!
```

### Backing services

Start the ones you need:

```bash
docker run -d --name rag-mongo  -p 27017:27017 mongo:7
docker run -d --name rag-redis  -p 6379:6379   redis:7-alpine
docker run -d --name rag-qdrant -p 6333:6333   qdrant/qdrant:v1.10.1
docker run -d --name rag-pg     -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=rag  pgvector/pgvector:pg16
```

### Configuration

Settings are loaded from a `.env` file via `pydantic-settings`. Create one at the project root —
`.env` is git-ignored, `.env.example` is not:

```dotenv
APP_NAME=mini-rag
FILE_MAX_SIZE_MB=10
FILE_ALLOWED_TYPES=["application/pdf","text/plain"]

# Providers
GENERATION_BACKEND=openai          # openai | cohere
EMBEDDING_BACKEND=openai
OPENAI_API_KEY=sk-...
COHERE_API_KEY=

GENERATION_MODEL_ID=gpt-4o-mini
EMBEDDING_MODEL_ID=text-embedding-3-small
EMBEDDING_MODEL_SIZE=1536

# Chunking / retrieval
CHUNK_SIZE=512
CHUNK_OVERLAP=64
RETRIEVAL_TOP_K=5

# Stores
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=rag
POSTGRES_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rag
VECTOR_DB_BACKEND=qdrant           # qdrant | pgvector
QDRANT_URL=http://localhost:6333

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

Never commit real keys — `.env` and `.env.*` are ignored by [.gitignore](.gitignore) precisely so
that this stays true by default.

### Running

```bash
# API (reload on change)
uv run uvicorn rag.main:app --reload --host 0.0.0.0 --port 8000

# Worker, in a second shell
uv run celery -A rag.celery_app worker --loglevel=info

# Task dashboard, optional
uv run celery -A rag.celery_app flower --port=5555
```

The API docs are then at <http://localhost:8000/docs>.

## Project layout

```
src/rag/
├── __init__.py          # package entry point (`rag` console script)
├── main.py              # FastAPI app factory, router + middleware wiring
├── config.py            # pydantic-settings, one Settings object for the app
├── routes/              # HTTP layer only — validate, delegate, serialize
├── models/              # document / chunk schemas and data-access objects
├── stores/
│   ├── llm/             # provider interface + OpenAI and Cohere implementations
│   └── vectordb/        # provider interface + Qdrant and pgvector implementations
├── controllers/         # ingestion, chunking, retrieval, prompt assembly
└── tasks/               # Celery tasks and the Celery app
```

The rule that keeps this honest: routes never call a provider SDK directly. They call a controller,
which calls an interface, which a store implements. Swapping Qdrant for pgvector — or OpenAI for
Cohere — then touches exactly one file.

## Tutorial roadmap

| # | Step | What it teaches |
| --- | --- | --- |
| 1 | Project setup, `uv`, settings | Reproducible envs; configuration as data, not constants |
| 2 | FastAPI skeleton, health & metrics | Layering, dependency injection, readiness vs liveness |
| 3 | File upload & validation | Size/type limits, streaming to disk, per-project storage |
| 4 | MongoDB models | Async data access, indexes, why chunks are their own collection |
| 5 | Parsing & chunking | Chunk size vs overlap, and what each one costs at retrieval |
| 6 | Celery pipeline | Moving slow work off the request path; retries and idempotency |
| 7 | Embeddings behind an interface | Provider abstraction; embedding dimension as a contract |
| 8 | Vector store: Qdrant | Collections, payload filtering, distance metrics |
| 9 | Retrieval & prompt assembly | top-k, context budgeting, grounding instructions, citations |
| 10 | Answer generation | Streaming responses, refusing to answer outside the context |
| 11 | Postgres + pgvector | Same interface, different backend; Alembic migrations |
| 12 | Observability | Prometheus metrics, Flower, tracing a slow query end to end |

## Notes on evaluation

A RAG system that "looks fine" in a demo fails quietly in two distinct places: retrieval brings
back the wrong chunks, or generation ignores the right ones. Keep a small fixed set of
question/expected-source pairs from the start and measure them separately — retrieval hit-rate for
the first, answer faithfulness for the second. Debugging the combined output alone tells you very
little about which half broke.

## License

Add the license of your choice before publishing.
