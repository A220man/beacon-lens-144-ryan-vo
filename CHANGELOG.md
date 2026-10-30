# Changelog

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