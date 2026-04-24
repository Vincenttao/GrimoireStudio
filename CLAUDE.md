# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Genesis Engine** — AI-native story generation system. Single-user local-first monolith: Python 3.12 + FastAPI backend, React 19 + TypeScript + Vite frontend, SQLite (WAL) for persistence, LiteLLM for multi-provider LLM access.

The user directs a recurring loop where AI-driven Character agents act in a world defined by "The Grimoire," orchestrated by a deterministic state machine ("The Maestro"), then rendered to prose by a "Camera" agent.

## Commands

**Backend** (run from repo root — `backend.main:app` imports assume this):
```bash
uv sync                                                              # install deps
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000  # dev server
uv run pytest backend/tests/ -v                                      # all tests
uv run pytest backend/tests/test_camera.py::TestCameraAgent::test_render_ir_block_omniscient_pov_returns_html -v  # single test
uv run pytest -m "not llm" -v                                        # skip real-LLM tests
ruff format backend/ && ruff check backend/ --fix                    # format + lint
```

**Frontend** (from `frontend/`):
```bash
npm install
npm run dev         # Vite dev server on :5173, proxies /api and /ws to :8000
npm run build       # tsc -b && vite build (type-check is part of build)
npm run lint        # ESLint
npm run test:e2e    # Playwright
```

**Pre-commit gate:** pytest + ruff + `npm run lint` must all pass (see `AGENT.md` §3.3).

## Configuration

LLM keys live in `.env` (copy from `.env.example`). Resolution order is **env vars > DB settings**. The frontend can override `LLM_API_BASE` per project via the Settings page. Common providers: OpenAI, Anthropic, DeepSeek, Alibaba DashScope (OpenAI-compatible endpoint).

## Architecture (the big picture)

The system decouples "story happens" from "story is written":

```
User intent → Muse (NL parse) → Maestro (orchestration loop) → Character agents
                                         ↓
                       IR Block (immutable structured script) → Camera (render to HTML)
                                         ↓
                                    Scribe (extract state deltas) → Grimoire
```

### Backend layering (`backend/`)
- `routers/` — HTTP + WebSocket handlers. One router per domain (`sandbox`, `muse`, `grimoire`, `storyboard`, `render`, `memory`, `settings`).
- `services/` — orchestration logic. `maestro_loop.py` runs the turn-based state machine; `llm_client.py` wraps LiteLLM with Pydantic-validated structured output; `camera_client.py` renders IR → HTML; `websocket_manager.py` owns connection state and the override/cut queues used by God's Hand.
- `crud/` — SQLite access. `entities.py` (soft delete via `is_deleted`), `storyboard.py` (story nodes + IR blocks, LexoRank ordering), `snapshots.py`, `branches.py`, `memory.py` (sqlite-vec), `scribe.py` (delta applier).
- `models.py` — all Pydantic V2 types. The `SandboxState` enum (IDLE → SPARK_RECEIVED → REASONING → CALLING_CHARACTER → EVALUATING → EMITTING_IR → COMMITTED) drives the Maestro state machine and is also mirrored in the frontend.
- `database.py` — `init_db()` runs on FastAPI lifespan startup; connections enforce `PRAGMA journal_mode=WAL`.

### Frontend layering (`frontend/src/`)
- Routing is **wouter** (not React Router). Switch is in `App.tsx`.
- No global store — `useState` plus a `wsManager` singleton pub/sub in `lib/ws.ts`. Pattern: `wsManager.on(event, cb)` returns an unsub you must call in the `useEffect` cleanup.
- `lib/api.ts` groups REST calls by domain (`sandboxApi`, `grimoireApi`, `storyboardApi`, `settingsApi`, `museApi`). `museApi.chat` is an async generator over SSE.
- Theming: custom Tailwind tokens (`grimoire-bg`, `grimoire-accent`, `grimoire-gold`) and shared utility classes in `index.css` (`.glass-card`, `.btn-glow`, `.btn-ghost`, `.btn-danger`, `.input-dark`). Framer Motion is the animation library.

### Cross-cutting patterns
- **Three-layer prompting** for Character agents (System persona → Scene context → Director override). When adding new agent prompts, respect this layering instead of inlining full prompts.
- **Snapshot chain** for world state — never `UPDATE` history rows; append a new snapshot. Branches are forks of the snapshot chain.
- **Immutable IR Blocks** — once `story_ir_blocks` is written, only `content_html` may be re-rendered. Don't mutate the action sequence.
- **LexoRank** string ordering lets nodes and IR blocks be inserted at any position without reindexing.
- **Singleton rows** — the `settings` table uses `id = "single_row_lock"`.
- **WebSocket events** (downstream: `STATE_CHANGE`, `TURN_STARTED`, `DISPATCH`, `CHAR_STREAM`, `SYS_DEV_LOG`, `SCENE_COMPLETE`, `ERROR`; upstream: `OVERRIDE`, `CUT`). Real-time UI is mandatory — no polling.

### Things that need to stay in sync across backend/frontend
- `SandboxState` enum: `backend/models.py` ↔ `frontend/src/lib/ws.ts`. Changing one without the other breaks the Monitor.
- WebSocket event shapes: `services/websocket_manager.py` ↔ `lib/ws.ts`.

## Project-specific constraints (don't violate)

From `GEMINI.md`, `AGENT.md`, `AGENTS.md`:
- **TDD is mandatory.** Red → Green → Refactor. Add a failing `pytest` *before* the implementation. Do not delete tests to make them pass.
- **Programmatic orchestration only.** The Maestro loop is an explicit FastAPI loop — no autonomous LLM routing / agent frameworks.
- **No external SaaS / observability** (no Langfuse, LangSmith, OpenTelemetry). Logging is local `loguru` + WebSocket.
- **No Redis, no microservices.** SQLite WAL + one FastAPI process.
- **No hardcoded Chinese prompts in logic** — use Jinja2 templates or constants.
- **Character output is first-person only.** No third-person narration in Character agent output.
- **Camera reads only the IR**, never the rendered HTML.
- **No `as any` / `@ts-ignore`** to silence type errors.
- **Strict Pydantic V2 validation** on every LLM I/O boundary.

## Documentation precedence

When docs conflict, follow this order:
1. `docs/SPEC.md`
2. `AGENT.md` (repo root — development workflow & TDD)
3. `GEMINI.md` (repo root — core mandates)
4. `docs/Architecture_Design.md`

There are also directory-scoped knowledge files worth reading before working in that area: `backend/AGENTS.md`, `frontend/AGENTS.md`, and the root `AGENTS.md` (overview / anti-patterns).

## Testing notes

- `pyproject.toml` sets `asyncio_mode = "auto"` — tests can be plain `async def`.
- The `llm` pytest marker gates tests that hit a real LLM API; CI and local fast loops should use `-m "not llm"`.
- DB tests use an autouse fixture that removes `grimoire.sqlite` between runs (see `backend/tests/test_crud.py`). Keep new DB tests consistent with this pattern rather than using an in-memory override.
- Mock LLM calls by patching `backend.services.llm_client.llm_client._generate_structured` (returns a Pydantic model, not a dict).
