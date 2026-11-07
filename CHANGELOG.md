# Changelog

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.3.0 — 2026-11-07

### Added
- Wiki generation feature with map/reduce pipeline
- WikiPage and WikiSection SQLAlchemy models with pgvector-ready schema
- MapCache model for content-addressable caching of map phase results
- WikiService with map phase (slug extraction, summarization, classification) and reduce phase (section merging)
- Content-addressable caching using SHA256 content hashes for map phase reprocessing avoidance
- REST API endpoints: POST /api/v1/wiki/generate, GET /api/v1/wiki, GET /api/v1/wiki/search, GET /api/v1/wiki/{id}, GET /api/v1/wiki/slug/{slug}, DELETE /api/v1/wiki/{id}
- Unit tests for wiki service (normalization, hashing, slug extraction, classification, cache behavior)
- API tests for wiki endpoints (validation, listing, search)

### Changed
- Updated PLAN.md and feature-plan.json to mark wiki-generation as complete
- Extended backend models with wiki-related tables

### Infrastructure
- Database schema migration for wiki_pages, wiki_sections, map_cache tables

## 1.2.0 — work-in-progress checkpoint
## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

# Beacon Lens - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-23

### Added
- FastAPI backend skeleton with `/health` and `/api/v1/health` endpoints
- React + TypeScript + Vite frontend with health status display
- Docker Compose configuration with PostgreSQL (pgvector), Keycloak, backend, frontend
- Backend tests (pytest + httpx) for health endpoints
- Frontend tests (vitest + React Testing Library) for App component
- Multi-stage Dockerfiles for backend and frontend with non-root users
- Environment template (.env.example)
- Comprehensive README with architecture diagram, install steps, API reference
- MIT License with author metadata
- pyproject.toml with author metadata
- package.json with author email
- Architecture: Clean separation of backend (FastAPI) and frontend (React)

### Infrastructure
- PostgreSQL 16 with pgvector extension for vector search
- Keycloak 26 for OIDC authentication
- Nginx reverse proxy for frontend with API proxy to backend
- Health checks on all services
- Non-root containers with minimal attack surface

### Planned (Next Iterations)
- RAG core: document upload, chunking, embedding, vector search
- Wiki generation: extract, summarize, classify, reduce pipeline
- Reasoning agent with tool use
- OIDC authentication with Keycloak integration
- Content-addressable caching for incremental reprocessing (Issue #1679)