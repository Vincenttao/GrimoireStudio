from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite
from loguru import logger

# We store the sqlite file in the local directory for the Genesis MVP
DB_PATH = "grimoire.sqlite"

# Only import when needed
SQLITE_VEC_AVAILABLE = None

# Check if sqlite_vec is available
try:
    # Don't import at module level to allow graceful degradation
    import sqlite_vec  # noqa: F401

    SQLITE_VEC_AVAILABLE = True
    logger.info("sqlite-vec is available")
except ImportError:
    SQLITE_VEC_AVAILABLE = False
    logger.warning("sqlite-vec not available, vector search functionality will be disabled")


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


from backend.models import (
    DefaultRenderMixer,
    LLMApiKeys,
    ModelRouting,
    PlatformProfile,
    ProjectSettings,
)

# ... (keep existing code)


async def get_project_settings(conn: aiosqlite.Connection) -> ProjectSettings:
    """
    Retrieves the singleton project settings from the database.
    If not found, initializes with defaults (Occam's Razor).
    """
    async with conn.execute("SELECT * FROM settings WHERE id = 'single_row_lock'") as cursor:
        row = await cursor.fetchone()
        if row:
            model_routing = None
            if "model_routing_json" in row.keys() and row["model_routing_json"]:
                model_routing = ModelRouting.model_validate_json(row["model_routing_json"])

            # V1.1 fields — tolerate missing columns (old DB)
            row_keys = row.keys()
            target_platform = PlatformProfile.QIDIAN
            if "target_platform" in row_keys and row["target_platform"]:
                try:
                    target_platform = PlatformProfile(row["target_platform"])
                except ValueError:
                    pass

            default_target_char_count = (
                row["default_target_char_count"]
                if "default_target_char_count" in row_keys
                and row["default_target_char_count"] is not None
                else 3000
            )
            default_max_sent_len = (
                row["default_max_sent_len"]
                if "default_max_sent_len" in row_keys and row["default_max_sent_len"] is not None
                else 30
            )
            ending_hook_guard_enabled = bool(
                row["ending_hook_guard_enabled"]
                if "ending_hook_guard_enabled" in row_keys
                and row["ending_hook_guard_enabled"] is not None
                else True
            )
            padding_detector_enabled = bool(
                row["padding_detector_enabled"]
                if "padding_detector_enabled" in row_keys
                and row["padding_detector_enabled"] is not None
                else True
            )
            daily_streak_count = (
                row["daily_streak_count"]
                if "daily_streak_count" in row_keys and row["daily_streak_count"] is not None
                else 0
            )
            last_commit_at = None
            if "last_commit_at" in row_keys and row["last_commit_at"]:
                from datetime import datetime as _dt

                try:
                    last_commit_at = _dt.fromisoformat(row["last_commit_at"])
                except ValueError:
                    pass

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
                target_platform=target_platform,
                default_target_char_count=default_target_char_count,
                default_max_sent_len=default_max_sent_len,
                ending_hook_guard_enabled=ending_hook_guard_enabled,
                padding_detector_enabled=padding_detector_enabled,
                daily_streak_count=daily_streak_count,
                last_commit_at=last_commit_at,
            )

        # Default initialization if table is empty
        default_settings = ProjectSettings(
            llm_api_keys=LLMApiKeys(),
            default_render_mixer=DefaultRenderMixer(
                pov_type="OMNISCIENT", style_template="热血爽文"
            ),
        )
        await conn.execute(
            """INSERT INTO settings (
                id, llm_model, model_routing_json, llm_api_keys_json, llm_api_base,
                max_turns, tension_threshold, default_render_mixer_json,
                target_platform, default_target_char_count, default_max_sent_len,
                ending_hook_guard_enabled, padding_detector_enabled,
                daily_streak_count, last_commit_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                default_settings.target_platform.value,
                default_settings.default_target_char_count,
                default_settings.default_max_sent_len,
                int(default_settings.ending_hook_guard_enabled),
                int(default_settings.padding_detector_enabled),
                default_settings.daily_streak_count,
                default_settings.last_commit_at.isoformat()
                if default_settings.last_commit_at
                else None,
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
        # Load sqlite-vec extension if available
        if SQLITE_VEC_AVAILABLE:
            try:
                import sqlite_vec

                await conn.execute("SELECT load_extension(?)", (sqlite_vec.load(conn),))
                logger.success("SQLite-vec extension loaded successfully")

                # Create memory vectors virtual table if extension is available
                await conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
                        id INTEGER PRIMARY KEY,
                        content_embedding float[384],
                        entity_id TEXT NOT NULL,
                        memory_text TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)

            except Exception as e:
                logger.error(
                    f"Failed to load sqlite-vec extension or create virtual table: {str(e)}"
                )
                logger.warning("Vector search functionality will be disabled")
        else:
            logger.info("sqlite-vec not available, skipping vector functionality")

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
        for stmt in [
            "ALTER TABLE settings ADD COLUMN llm_model TEXT NOT NULL DEFAULT 'gpt-4'",
            "ALTER TABLE settings ADD COLUMN max_turns INTEGER NOT NULL DEFAULT 12",
            "ALTER TABLE settings ADD COLUMN tension_threshold REAL NOT NULL DEFAULT 0.8",
            "ALTER TABLE settings ADD COLUMN model_routing_json TEXT",
            # V1.1 新增列
            "ALTER TABLE settings ADD COLUMN target_platform TEXT DEFAULT 'QIDIAN'",
            "ALTER TABLE settings ADD COLUMN default_target_char_count INTEGER DEFAULT 3000",
            "ALTER TABLE settings ADD COLUMN default_max_sent_len INTEGER DEFAULT 30",
            "ALTER TABLE settings ADD COLUMN ending_hook_guard_enabled INTEGER DEFAULT 1",
            "ALTER TABLE settings ADD COLUMN padding_detector_enabled INTEGER DEFAULT 1",
            "ALTER TABLE settings ADD COLUMN daily_streak_count INTEGER DEFAULT 0",
            "ALTER TABLE settings ADD COLUMN last_commit_at TEXT",
            # Entities V1.1 新增列
            "ALTER TABLE entities ADD COLUMN voice_signature_json TEXT",
        ]:
            try:
                await conn.execute(stmt)
            except aiosqlite.Error:
                pass

        # V1.1 新表: soft_patches
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS soft_patches (
                patch_id TEXT PRIMARY KEY,
                target_entity_id TEXT NOT NULL,
                target_path TEXT NOT NULL,
                old_value_json TEXT NOT NULL,
                new_value_json TEXT NOT NULL,
                author_note TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                merged_into_snapshot_id TEXT
            )
        """)

        # V1.1 新表: scenes (Chapter -> Scene -> IRBlock 三级层次)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                scene_id TEXT PRIMARY KEY,
                chapter_id TEXT NOT NULL,
                lexorank TEXT NOT NULL,
                beat_type TEXT NOT NULL,
                spark_id TEXT,
                ir_block_id TEXT,
                state TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL
            )
        """)

        # V1.1 新表: chapter_beat_logs (爽点节奏表, V2.0 使用)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chapter_beat_logs (
                chapter_id TEXT PRIMARY KEY,
                lexorank TEXT NOT NULL,
                beat_types_json TEXT NOT NULL,
                committed_at TEXT NOT NULL
            )
        """)

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

        # Table: Branches (for create_branch feature - V2.0)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS branches (
                branch_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                origin_snapshot_id TEXT,
                parent_branch_id TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        # Table: Snapshots (for rollback feature - V2.0)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id TEXT PRIMARY KEY,
                branch_id TEXT NOT NULL,
                parent_snapshot_id TEXT,
                triggering_block_id TEXT,
                grimoire_state_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        await conn.commit()
