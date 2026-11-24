# Agentic-RAG

[![CI](https://github.com/n09tal/Agentic-RAG/actions/workflows/ci.yml/badge.svg)](https://github.com/n09tal/Agentic-RAG/actions/workflows/ci.yml)

An AI agent that answers questions about headphones using real Amazon reviews
(Amazon Reviews 2023). Every number is recomputable from the database, and every quote
links back to the original review.

> **Status:** the local development environment is ready (FastAPI backend, PostgreSQL + pgvector,
> Next.js frontend, CI). Retrieval and agent features are in progress.

## Tech stack

- **Backend:** Python 3.12, FastAPI, Pydantic, psycopg
- **Database:** PostgreSQL 17 + pgvector, run with Docker Compose
- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS
- **Tooling:** uv, npm, pytest, ESLint, GitHub Actions

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Node.js 22
- Docker Desktop

### 1. Start the database

```bash
cp .env.example .env        # set your own password in both places
docker compose up -d --wait
```

### 2. Start the backend

```bash
uv sync
uv run uvicorn backend.api.main:app --reload
```

`http://127.0.0.1:8000/ready` should return `{"status":"ready","database":"ok"}`.

### 3. Start the frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000` (use `localhost`, not `127.0.0.1`).

### Run the checks

```bash
uv run pytest
cd frontend && npm run lint && npm run build
```

## Project layout

| Path | Purpose |
|---|---|
| `frontend/` | Next.js web app |
| `backend/api/` | FastAPI entry point |
| `backend/agent/` | Agent state and graph (planned) |
| `backend/tools/amazon/` | Business tools (planned) |
| `backend/mcp/` | MCP server and client (planned) |
| `db/` | Database migrations (planned) |
| `ingest/` | Data import and embedding (planned) |
| `tests/` | Unit and integration tests |
| `evals/` | Evaluation questions and results (planned) |
| `deploy/` | Deployment configuration (planned) |

## Docs

- [Requirements: demo questions and answer shape](docs/requirements.md)