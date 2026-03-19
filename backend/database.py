import aiosqlite
from loguru import logger
from typing import AsyncGenerator
from contextlib import asynccontextmanager

# We store the sqlite file in the local directory for the Genesis MVP
DB_PATH = "grimoire.sqlite"


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Acquires an asynchronous connection to the monolithic SQLite database.
    WARNING: Adheres to AGENT.md Strict Mutex rules and SPEC.md §6.1
    Executes 'PRAGMA journal_mode=WAL;' immediately to prevent 'Database is locked' errors
    during concurrent reads (e.g., SSE streams) and writes (e.g., Scribe updates).
    """
    conn = await aiosqlite.connect(DB_PATH)
    try:
        # Crucial for concurrent async reads/writes
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA synchronous=NORMAL;")
        # Provide dict-like access to rows
        conn.row_factory = aiosqlite.Row
        yield conn
    finally:
        await conn.close()


from backend.models import ProjectSettings, LLMApiKeys, DefaultRenderMixer, ModelRouting
import json

# ... (keep existing code)


async def get_project_settings(conn: aiosqlite.Connection) -> ProjectSettings:
    """
    Retrieves the singleton project settings from the database.
    If not found, initializes with defaults (Occam's Razor).
    """
    async with conn.execute(
        "SELECT * FROM settings WHERE id = 'single_row_lock'"
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            model_routing = None
            if "model_routing_json" in row.keys() and row["model_routing_json"]:
                model_routing = ModelRouting.model_validate_json(
                    row["model_routing_json"]
                )

            return ProjectSettings(
                id=row["id"],
                llm_model=row["llm_model"],
                model_routing=model_routing,
                llm_api_keys=LLMApiKeys.model_validate_json(row["llm_api_keys_json"]),
                llm_api_base=row["llm_api_base"],
                max_turns=row["max_turns"],
                tension_threshold=row["tension_threshold"],
                default_render_mixer=DefaultRenderMixer.model_validate_json(
                    row["default_render_mixer_json"]
                ),
            )

        # Default initialization if table is empty
        default_settings = ProjectSettings(
            llm_api_keys=LLMApiKeys(),
            default_render_mixer=DefaultRenderMixer(
                pov_type="OMNISCIENT", style_template="Standard"
            ),
        )
        await conn.execute(
            "INSERT INTO settings (id, llm_model, model_routing_json, llm_api_keys_json, llm_api_base, max_turns, tension_threshold, default_render_mixer_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                default_settings.id,
                default_settings.llm_model,
                default_settings.model_routing.model_dump_json()
                if default_settings.model_routing
                else None,
                default_settings.llm_api_keys.model_dump_json(),
                default_settings.llm_api_base,
                default_settings.max_turns,
                default_settings.tension_threshold,
                default_settings.default_render_mixer.model_dump_json(),
            ),
        )
        await conn.commit()
        return default_settings


async def init_db() -> None:
    """
    Initializes the database schema.
    To be called during application startup.
    Creates necessary tables if they don't exist yet.
    """
    logger.info(f"Initializing SQLite database at {DB_PATH}")
    async with get_db_connection() as conn:
        # Table: Entities
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                base_attributes_json TEXT NOT NULL,
                current_status_json TEXT NOT NULL,
                is_deleted BOOLEAN NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Table: StoryNodes
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS story_nodes (
                node_id TEXT PRIMARY KEY,
                branch_id TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                lexorank TEXT NOT NULL,
                parent_node_id TEXT
            )
        """)

        # Table: StoryIRBlocks
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS story_ir_blocks (
                block_id TEXT PRIMARY KEY,
                chapter_id TEXT NOT NULL,
                lexorank TEXT NOT NULL,
                summary TEXT NOT NULL,
                involved_entities_json TEXT NOT NULL,
                scene_context_json TEXT NOT NULL,
                action_sequence_json TEXT NOT NULL,
                content_html TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Table: Settings
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id TEXT PRIMARY KEY,
                llm_model TEXT NOT NULL DEFAULT 'gpt-4',
                model_routing_json TEXT,
                llm_api_keys_json TEXT NOT NULL,
                llm_api_base TEXT,
                max_turns INTEGER NOT NULL DEFAULT 12,
                tension_threshold REAL NOT NULL DEFAULT 0.8,
                default_render_mixer_json TEXT NOT NULL
            )
        """)

        # Simple migration for existing DBs
        try:
            await conn.execute(
                "ALTER TABLE settings ADD COLUMN llm_model TEXT NOT NULL DEFAULT 'gpt-4'"
            )
        except:
            pass
        try:
            await conn.execute(
                "ALTER TABLE settings ADD COLUMN max_turns INTEGER NOT NULL DEFAULT 12"
            )
        except:
            pass
        try:
            await conn.execute(
                "ALTER TABLE settings ADD COLUMN tension_threshold REAL NOT NULL DEFAULT 0.8"
            )
        except:
            pass
        try:
            await conn.execute(
                "ALTER TABLE settings ADD COLUMN model_routing_json TEXT"
            )
        except:
            pass

        # Table: Scratchpad Checkpoints (for crash recovery)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS scratchpad_checkpoints (
                spark_id TEXT PRIMARY KEY,
                turn_logs_json TEXT NOT NULL,
                pending_facts_json TEXT NOT NULL,
                current_turn INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        await conn.commit()
