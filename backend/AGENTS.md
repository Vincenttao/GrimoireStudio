# BACKEND KNOWLEDGE BASE

**Stack:** Python 3.12 + FastAPI + aiosqlite + LiteLLM + pytest

## STRUCTURE

```
backend/
├── main.py          # FastAPI app entry, router registration
├── models.py        # Pydantic models (all domain types)
├── database.py      # SQLite WAL connection + schema
├── routers/         # HTTP/WebSocket handlers
│   ├── sandbox.py   # Orchestration + WebSocket
│   ├── muse.py      # AI chat (SSE streaming)
│   ├── grimoire.py  # Entity CRUD
│   ├── storyboard.py # Story nodes/IR blocks
│   └── settings.py  # Project config (singleton)
├── crud/            # Data access layer
│   ├── entities.py  # Entity CRUD + soft delete
│   ├── storyboard.py # StoryNode & IRBlock CRUD
│   └── scribe.py    # State delta applier
├── services/        # Business logic
│   ├── llm_client.py     # LiteLLM structured output
│   ├── maestro_loop.py   # Orchestration loop
│   └── websocket_manager.py # WS connection + override queues
└── tests/           # pytest suite (14 tests)
```

## WHERE TO LOOK

| Task | File |
|------|------|
| Add REST endpoint | `routers/<feature>.py` |
| Add WebSocket event | `services/websocket_manager.py` |
| Add LLM prompt | `services/llm_client.py` |
| Add data model | `models.py` |
| Add DB operation | `crud/<entity>.py` |
| Add test | `tests/test_<feature>.py` |

## API PATTERNS

**Router Registration** (main.py):
```python
app.include_router(sandbox.router, prefix="/api/v1/sandbox", tags=["Sandbox"])
```

**Response Wrapping:**
```python
return {"entity": entity.model_dump()}
return {"entities": [...]}
```

**WebSocket Events:**
- Downstream: `STATE_CHANGE`, `TURN_STARTED`, `DISPATCH`, `CHAR_STREAM`, `SYS_DEV_LOG`, `SCENE_COMPLETE`, `ERROR`
- Upstream: `Action: CUT`, `Action: OVERRIDE`

## KEY CONVENTIONS

**3-Layer Prompting** (Character agent):
1. System layer — persona, stats
2. Scene layer — context, history
3. Director layer — override notes

**Soft Delete:** `is_deleted = True` on entities, never hard delete

**Lexorank:** String-based ordering for story nodes/blocks

**Singleton Settings:** `id = "single_row_lock"` in settings table

## ANTI-PATTERNS

- **No hardcoded prompts** — Extract to Jinja2 or constants
- **No `as any` / `@ts-ignore`** — Strict Pydantic validation
- **No third-person Character output** — First-person only
- **No `UPDATE` on history** — Use snapshots

## LLM CLIENT

`services/llm_client.py`:
- `_generate_structured()` — Generic wrapper with robust JSON parsing
- Auto-strips markdown blocks
- Maps hallucinated field names (e.g., `inner_monologue` → `intent`)
- Supports OpenAI, Anthropic, DeepSeek, custom endpoints

## DATABASE

`database.py`:
- `get_db_connection()` — Async context manager with WAL mode
- `init_db()` — Creates tables on startup
- Tables: `entities`, `story_nodes`, `story_ir_blocks`, `settings`

## TESTS

```bash
uv run pytest backend/tests/ -v
```

- All tests use `@pytest.mark.asyncio`
- Fixtures in `test_crud.py` (`db_setup` with autouse)
- API tests use `httpx.AsyncClient` with `ASGITransport`
- Mock LLM with `monkeypatch.setattr`