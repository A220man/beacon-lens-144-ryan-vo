# Beacon Lens — Ryan Vo

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


**Beacon Lens** — Ryan Vo | AI & Machine Learning

Open-source LLM knowledge platform: turn raw documents into a queryable RAG, an autonomous reasoning agent, and a self-maintaining Wiki.

## Problem

Organizations accumulate vast amounts of unstructured knowledge in documents (PDFs, wikis, codebases, tickets). Finding answers requires either manual search or brittle keyword matching. LLMs can reason over this knowledge but need structured retrieval, citation, and incremental updates without full reprocessing.

## Approach

Beacon Lens implements three integrated AI/ML workflows:

1. **RAG Pipeline** — Document ingestion → chunking → embedding → vector search with pgvector. Content-addressable caching avoids recomputing embeddings for unchanged chunks.
2. **Wiki Generation** — Per-document map phase (extract, summarize, classify) → cross-document reduce phase (merge, deduplicate). Cached map outputs enable incremental wiki updates.
3. **Reasoning Agent** — Autonomous agent with tool use (search, wiki lookup, chunk fetch) for multi-step question answering with citations.

## Architecture

```mermaid
graph TB
    subgraph Client
        UI[React + TypeScript + Vite]
    end

    subgraph API
        BE[FastAPI Backend]
        Auth[OIDC/Keycloak]
    end

    subgraph Data
        PG[(PostgreSQL + pgvector)]
        KC[Keycloak]
    end

    subgraph AI
        LLM[LLM Provider API]
        Embed[Embedding Model]
        VLM[Vision-Language Model]
    end

    UI --> BE
    UI --> Auth
    BE --> PG
    BE --> KC
    BE --> LLM
    BE --> Embed
    BE --> VLM
    Auth --> KC
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node 24+ (for local frontend development)
- Python 3.12+ (for local backend development)

### Using Docker Compose (Recommended)

```bash
# Clone and navigate
cd beacon-lens-144-ryan-vo

# Copy environment template
cp .env.example .env

# Start all services
docker compose up -d

# Services available at:
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Keycloak Admin: http://localhost:8080 (admin/admin)
```

### Local Development

#### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://beacon:beacon@localhost:5432/beacon_lens
export KEYCLOAK_URL=http://localhost:8080
# ... other vars from .env.example

# Run with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

#### Backend Tests

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v
```

#### Frontend Tests

```bash
cd frontend
npm test
```

#### Full Test Suite

```bash
# From repo root
docker compose -f docker-compose.yaml -f docker-compose.test.yaml up --build --abort-on-container-exit
```

## API Reference

### Health

- `GET /health` — Service health check
- `GET /api/v1/health` — API health check

### Knowledge Bases (Planned)

- `POST /api/v1/knowledge-bases` — Create knowledge base
- `GET /api/v1/knowledge-bases` — List knowledge bases
- `GET /api/v1/knowledge-bases/{id}` — Get knowledge base
- `POST /api/v1/knowledge-bases/{id}/documents` — Upload document
- `POST /api/v1/knowledge-bases/{id}/query` — Semantic search
- `POST /api/v1/knowledge-bases/{id}/reprocess` — Incremental reprocess

### Wiki (Planned)

- `GET /api/v1/knowledge-bases/{id}/wiki` — List wiki pages
- `GET /api/v1/knowledge-bases/{id}/wiki/{slug}` — Get wiki page

### Agent (Planned)

- `POST /api/v1/agent/query` — Ask agent a question
- `GET /api/v1/agent/sessions` — List reasoning sessions

## AI/ML Evaluation

### Reproducible Baseline (Planned)

```bash
# Run evaluation on sample dataset
cd backend
python -m eval.run --dataset eval/data/sample.jsonl --output eval/results.json
```

**Dataset Provenance**: Curated from public technical documentation (Python, Kubernetes, PostgreSQL) with human-annotated Q&A pairs.

**Baseline Metrics** (target):
- RAG Retrieval: Recall@5 > 0.85, MRR > 0.75
- Answer Accuracy: F1 > 0.80 on factoid Q&A
- Wiki Quality: Human eval > 4.0/5.0 on coherence, completeness

**Failure Cases**:
- Ambiguous multi-hop queries requiring disambiguation
- Out-of-domain queries (hallucination risk)
- Very long documents exceeding context window

## Security Limitations

- Demo mode binds to localhost only; refuses to start in production without proper TLS and secrets
- LLM API keys server-side only; never exposed to frontend
- OIDC tokens validated with signature/issuer/audience checks
- HttpOnly SameSite cookies with CSRF protection for state-changing operations
- No hardcoded credentials; all secrets via environment variables
- Input validation and sanitization on all endpoints

## Provider Configuration

| Provider | LLM_PROVIDER | LLM_MODEL Example | LLM_BASE_URL |
|----------|--------------|-------------------|--------------|
| OpenAI | openai-compatible | gpt-4o-mini | https://api.openai.com/v1 |
| Anthropic | anthropic | claude-3-haiku-20240307 | https://api.anthropic.com |
| Gemini | gemini | gemini-1.5-flash | https://generativelanguage.googleapis.com |
| Ollama | ollama | llama3.1 | http://localhost:11434/v1 |
| LiteLLM/OpenRouter | openai-compatible | openrouter/auto | https://openrouter.ai/api/v1 |

## SSO/SAML Setup

Keycloak supports upstream SAML IdPs through identity brokering:

1. In Keycloak Admin Console: Identity Providers → Add SAML v2.0
2. Configure IdP metadata (entity ID, SSO URL, certificate)
3. Map SAML attributes to Keycloak user attributes
4. Enable "First Login Flow" for user registration
5. Test with SP-initiated and IdP-initiated flows

## Backup & Restore

```bash
# Backup PostgreSQL
docker exec beacon-lens-postgres pg_dump -U beacon beacon_lens > backup.sql

# Restore
docker exec -i beacon-lens-postgres psql -U beacon beacon_lens < backup.sql
```

## TLS Reverse Proxy Requirements

For production, terminate TLS at a reverse proxy (nginx, Traefik, Caddy):

- Proxy `https://your-domain.com` → `http://frontend:80`
- Proxy `https://your-domain.com/api` → `http://backend:8000`
- Proxy `https://your-domain.com/auth` → `http://keycloak:8080`
- Forward `X-Forwarded-Proto`, `X-Forwarded-For`, `Host` headers
- Configure Keycloak `PROXY_ADDRESS_FORWARDING=true`

## License

MIT License — Copyright (c) 2026 Ryan Vo <ryandtvo@gmail.com>

---

*Beacon Lens — Ryan Vo | AI & Machine Learning*