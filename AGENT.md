
**Context:** Grimoire Studio (v1.5) - Project Alchemist

**Docs:** `SPEC.md` (The Single Source of Truth)

## Project Structure & Module Organization

- **Backend (`/backend`):** FastAPI (Async), SQLModel, PostgreSQL (`pgvector`), Jinja2.
- **Frontend (`/frontend`):** React 18, TypeScript, Vite, Tiptap (Headless), TailwindCSS + Shadcn/ui.
- **Infrastructure:** Docker Compose at root.
- **Prompt Engine:** `/backend/app/core/prompts/templates`. **Strict Rule:** No hardcoded prompts in Python files. Logic lives in Jinja2.

## Tech Stack & Environment Guidelines

- **Runtime:** Python 3.11+ (Backend), Node 20+ (Frontend).
    
- **Package Managers:** `poetry` (Backend), `pnpm` (Frontend).
    
- **Database:** PostgreSQL 15+ with `pgvector` extension enabled.
    
- **Auth:** `python-jose` (JWT) + `passlib[bcrypt]`.
    
- **AI SDK:** OpenAI Python SDK (Standardized for OpenRouter/DeepSeek compatibility).
    

## Coding Style & Naming Conventions

### Backend (Python)

- **Type Hints:** Strict typing required. Use `typing.List`, `typing.Optional`, or modern `list[]` syntax consistently.
    
- **Models:** Use `SQLModel` for DB tables. Pydantic `BaseModel` for API Schemas (`schemas/`).
    
- **Async:** All API endpoints must be `async def`. Database calls use `await session.exec(...)`.
    
- **Variable Naming:** `snake_case` for variables/functions, `PascalCase` for Classes.
    
- **Rank:** Always name rank fields `rank`. Type is **ALWAYS** `str` (LexoRank), never `float` or `int`.
    

### Frontend (TypeScript/React)

- **State Management (Crucial):**
    
    - **Tiptap:** The **Single Source of Truth** for document content (Chapters, Blocks, Text).
        
    - **Zustand:** Only for global UI state (Sidebar, Auth, Flags). **Never** duplicate document content into Zustand.
        
- **Components:** Functional components only. Use Hooks.
    
- **Styling:** TailwindCSS via `clsx` or `cn()` utility.
    

## Security & Tenancy (The Golden Rules)

1. **Strict Ownership Chain:**
    
    - **Never** retrieve a sub-resource (Chapter, Entity, Block) by ID alone.
        
    - **Must** Join `Project` and check `Project.owner_id == current_user.id`.
        
    - _Bad:_ `session.get(Chapter, id)`
        
    - _Good:_ `session.exec(select(Chapter).join(Project).where(Chapter.id == id, Project.owner_id == user.id))`
        
2. **Error Masking:**
    
    - If a resource belongs to another tenant, return **404 Not Found**, NOT 403 Forbidden. Do not leak resource existence.
        
3. **Vector Isolation:**
    
    - All RAG queries must include `metadata={"project_id": ...}` filter.
        

## Data Integrity & Architecture

### 1. LexoRank (Ordering)

- **String Only:** Ranks are alphanumeric strings (e.g., `"0|h00000:"`).
    
- **Forbidden:** Do not use integer increments or floating-point math for ordering.
    
- **Buckets:** In v1.5, hardcode the bucket to `"0|"`.
    
- **Sorting:** Always `ORDER BY rank ASC` using standard string collation.
    

### 2. The Slot Machine (Block Logic)

- **Atomic Updates:** When updating a block, if `selected_variant_index` changes, `content_snapshot` **MUST** be updated in the same transaction.
    
- **Snapshot Priority:** The Backend RAG engine reads `content_snapshot` (fast), not the JSON `variants` array (slow).
    
- **Variant Immutability:** AI-generated variants are append-only. User edits create a new `USER_CUSTOM` variant or update an existing `USER_CUSTOM` variant in-place.
    

### 3. The Ritual (Generation)

- **JSON Enforcement:** All LLM calls must use `response_format={ "type": "json_object" }`.
    
- **Jinja2 Routing:** Select templates based on `NarrativeMode`. Do not construct prompt strings via string concatenation.
    

## Testing Guidelines

- **Backend:** `pytest`.
    
    - **Mocking:** All external LLM calls must be mocked unless explicitly running a "Live" test.
        
    - **Tenancy:** Every endpoint test must verify that User A cannot access User B's data.
        
    - **LexoRank:** Verify string sorting logic (`"0|a"` < `"0|b"`).
        
- **Frontend:** `npm run test` (Vitest).
    
    - **SlotMachineNode:** Test `updateAttributes` and ensure it does _not_ trigger Zustand updates.
        
    - **Integration:** Mock API responses for `/generation/beat`.
        

## Multi-Agent Safety (Git Workflow)

- **No Stashing:** Do not `git stash` or `git pull --autostash` unless explicitly requested.
    
- **State Awareness:** Assume other agents are working on different files. Scope commits strictly to the task at hand.
    
- **Rebase:** Prefer `git pull --rebase origin main` to keep history linear.
    
- **Commit Messages:** Use Conventional Commits (e.g., `feat(backend): add lexorank utility`, `fix(editor): resolve tiptap sync issue`).
    

## Agent-Specific Notes (Troubleshooting & FAQs)

- **"Where is the prompt?"**: Look in `backend/app/core/prompts/templates/`. Do not edit `llm_service.py` for prompt wording changes.
    
- **"How do I sort chapters?"**: Use `chapter.rank` (String comparison).
    
- **"User edited the text, now RAG is wrong"**: Check if the frontend sent the `content_snapshot` in the PATCH request. The snapshot must match the editor state.
    
- **"Entity Aliases"**: When updating entities, use Set Arithmetic (Add/Delete sets) to handle aliases. Do not nuke and rebuild the list unless necessary.
    
- **Scrying Glass**: Logic is "Tiered". Tier 1 (Manual @) -> Tier 2 (Context Keywords) -> Tier 3 (Temporal/Rank Logic).
    
- **Schema Changes**: If you modify `SQLModel` classes, you **MUST** generate an Alembic migration: `alembic revision --autogenerate -m "message"`.
    

## Build & Run Commands

- **Start DB:** `docker-compose up -d`
    
- **Backend Dev:** `cd backend && poetry run uvicorn app.main:app --reload`
    
- **Frontend Dev:** `cd frontend && pnpm dev`
    
- **Run Tests:** `pytest` (Backend) / `pnpm test` (Frontend)
    
- **Database Shell:** `docker exec -it grimoire-db psql -U postgres -d grimoire`