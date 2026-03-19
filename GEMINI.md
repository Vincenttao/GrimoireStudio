# Genesis Engine Project Mandates

## Core Principles
- **Programmatic Orchestration:** The Maestro must use explicit loops in FastAPI. No autonomous LLM routing.
- **Single-User Monolith:** No microservices. Agents communicate via internal function calls within the same FastAPI process.
- **Strict Mutex & Locks:** Enforce turn-based exclusive locks and manuscript read-only locks during inference.
- **Snapshot Chain:** Use a linear snapshot model in SQLite for world state. No complex Event Sourcing or `UPDATE` on history.
- **Immutable Story IR:** Narrative logic (action sequence) is immutable once generated. Only `content_html` can be refined.

## Technical Standards
- **SQLite WAL Mode:** Must execute `PRAGMA journal_mode=WAL;` on connection.
- **Pydantic V2:** Strict Schema enforcement for all LLM I/O.
- **Prompt Isolation:** No hardcoded Chinese prompts in logic; use Jinja2 or constants.
- **WebSocket/SSE:** Mandatory for real-time inference feedback. No AJAX polling.
- **No External SaaS:** Use local `loguru` and WebSocket logs. No LangSmith/LangSmith.

## Development Workflow
- **Research -> Strategy -> Execution** (Plan -> Act -> Validate).
- **TDD Mandate:** Every feature or bug fix MUST have a corresponding `pytest`.
- **Validation:** Run `pytest`, `ruff`, and `npm run typecheck` before concluding tasks.
- **Documentation Precedence:** `docs/SPEC.md` > `docs/AGENT.md` > `docs/Architecture_Design.md`.

## Known Constraints
- V1.0 focuses on short stories; no vector RAG or `sqlite-vec`.
- Single-user local-first architecture.
