# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-19
**Commit:** 7e14219
**Branch:** main

## OVERVIEW

Genesis Engine — AI-native story generation system. Single-user monolith with Python FastAPI backend, React/TypeScript frontend. Uses LiteLLM for multi-provider LLM support with structured output enforcement.

## STRUCTURE

```
grimoire/
├── backend/        # FastAPI monolith (Python)
├── frontend/       # React + Vite (TypeScript)
├── docs/           # Specs, PRD, architecture docs
└── *.py            # Utility scripts at root (move to backend/scripts/)
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Add API endpoint | `backend/routers/*.py` |
| Add LLM logic | `backend/services/llm_client.py` |
| Add React component | `frontend/src/components/` |
| Add page/route | `frontend/src/pages/` |
| Modify data models | `backend/models.py` |
| Change DB schema | `backend/database.py` |
| LLM prompts | `backend/services/llm_client.py` |
| WebSocket events | `backend/services/websocket_manager.py`, `frontend/src/lib/ws.ts` |

## COMMANDS

```bash
# Backend (from project root)
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
uv run pytest backend/tests/ -v          # Run tests
ruff format backend/ && ruff check backend/ --fix

# Frontend
cd frontend && npm run dev               # Dev server (port 5173)
npm run build                            # Type-check + build
npm run lint                             # ESLint
```

## KEY ARCHITECTURE PATTERNS

**Backend Layers:**
- `routers/` — HTTP/WebSocket handlers
- `crud/` — Database operations
- `services/` — Business logic (LLM, Maestro loop, WS manager)

**Frontend:**
- `pages/` — Route-level components
- `components/` — Reusable UI
- `lib/` — API client, WebSocket manager, utilities

**State Machine:** `SandboxState` enum (9 states) — IDLE → SPARK_RECEIVED → REASONING → CALLING_CHARACTER → EVALUATING → EMITTING_IR → COMMITTED

## ANTI-PATTERNS (THIS PROJECT)

- **No external SaaS** — No Langfuse, LangSmith, OpenTelemetry
- **No Redis** — SQLite WAL only
- **No polling** — WebSocket/SSE mandatory
- **No third-person in Character output** — First-person dialogue only
- **No autonomous LLM routing** — Programmatic orchestration with explicit loops
- **No microservices** — Single FastAPI process for all agents

## VALIDATION WORKFLOW

Per `GEMINI.md`:
1. `pytest backend/tests/ -v`
2. `ruff format backend/ && ruff check backend/ --fix`
3. `cd frontend && npm run lint`

## NOTES

- Documentation hierarchy: `docs/SPEC.md` > `docs/AGENT.md` > `docs/Architecture_Design.md`
- `SandboxState` duplicated in backend (`models.py`) and frontend (`ws.ts`) — sync when modifying
- SQLite file: `grimoire.sqlite` at project root
- Vite proxies `/api` and `/ws` to `localhost:8000`