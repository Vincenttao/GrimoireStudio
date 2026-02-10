# Grimoire Studio (Project Alchemist)

**Grimoire Studio** is a next-generation "Glass Box & Co-Pilot" writing platform designed to transform AI-assisted creative writing from a "black box gamble" into transparent, precise orchestration. 

While existing tools often lead to "context amnesia" or "voice drift," Grimoire Studio provides authors with a structured workflow and high observability, ensuring narrative consistency and stylistic integrity.

## 核心愿景 | Core Vision
- **Glass Box:** Full visibility into AI context, RAG (Retrieval-Augmented Generation) hits, and decision-making logic.
- **Co-Pilot:** A collaborative workflow where the AI provides tactical variations (Narrative Modes) rather than just random completions.
- **Precision:** Maintaining world-building consistency through a dynamic entity database.

---

## 核心功能 | Key Features

### 1. The Grimoire (Dynamic Knowledge Base)
- **Entity Management:** Track characters, locations, items, and lore.
- **True Names & Aliases:** Advanced mapping (e.g., "Bruce" and "Batman" point to the same entity) to ensure AI recognition.
- **Temporal Relationships:** Dynamic relationship tracking that evolves with the story's timeline (LexoRank based).

### 2. The Ritual (Generation Engine)
- **Narrative Compass:** Five specialized modes (Standard, Conflict Injector, Sensory Lens, Focus Beam, and Fractal Expander) based on creative writing theory.
- **Slot Machine Interface:** Single-shot generation of three distinct variants, allowing authors to "spin" through options in-place.
- **Smart Context Smoothing:** Automatically adjusts the transition between blocks when a new variant is selected.

### 3. Scrying Glass (Observability)
- **Context Inspector:** Visualizes the AI's lookback window and active RAG hits.
- **Decision Explainer:** Explains why a specific variant was generated (e.g., "Injecting External Conflict").
- **Manual Intervention:** @Mention entities to force their inclusion in the context.

---

## 技术栈 | Tech Stack

### Backend
- **Framework:** FastAPI (Async Python 3.11+)
- **Database:** PostgreSQL with `pgvector` for semantic search.
- **ORM:** SQLModel (SQLAlchemy + Pydantic).
- **Prompting:** Jinja2 templates for logic-separated prompt engineering.
- **Security:** JWT-based authentication with strict multi-tenant isolation.

### Frontend
- **Framework:** React 18 + TypeScript + Vite.
- **Editor Engine:** Tiptap (ProseMirror-based headless editor).
- **State Management:** Zustand (for UI/Auth) + Tiptap's internal state (as the single source of truth for content).
- **UI:** TailwindCSS + Shadcn/ui.

---

## 开发计划 | Development Plan

### Phase 1: Foundation & Security (SaaS 基石)
- [x] Infrastructure setup (Docker + Postgres/pgvector).
- [x] Multi-tenant authentication system (JWT).
- [x] Project and tenancy isolation logic.

### Phase 2: The Brain (Core Logic)
- [x] **The Grimoire:** Temporal RAG and entity lifecycle management.
- [x] **The Ritual:** Jinja2-based prompt engine and multi-variant generation API.
- [x] **Style Anchors:** RAG-enabled few-shot style profiling.

### Phase 3: Frontend & Interaction (交互层)
- [ ] **Grimoire Editor:** Custom Tiptap extensions for the "Slot Machine" node.
- [ ] **Scrying Glass:** Real-time observability sidebar linked to editor cursor.
- [ ] **Smart Smoothing:** Logic for automatic narrative transition adjustment.

---

## 快速开始 | Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (Poetry)
- Node.js 20+ (pnpm)

### Setup
1. **Infrastructure:**
   ```bash
   docker-compose up -d
   ```
2. **Backend:**
   ```bash
   cd backend
   poetry install
   poetry run alembic upgrade head
   poetry run uvicorn app.main:app --reload
   ```
3. **Frontend:**
   ```bash
   cd frontend
   pnpm install
   pnpm dev
   ```

---

## 许可证 | License
Proprietary - All Rights Reserved.
