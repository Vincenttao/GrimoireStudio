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

async def init_db() -> None:
    """
    Initializes the database schema.
    To be called during application startup.
    Creates necessary tables if they don't exist yet.
    """
    logger.info(f"Initializing SQLite database at {DB_PATH}")
    async with get_db_connection() as conn:
        # Table: Entities
        await conn.execute('''
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
        ''')
        
        # Table: StoryNodes
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS story_nodes (
                node_id TEXT PRIMARY KEY,
                branch_id TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                lexorank TEXT NOT NULL,
                parent_node_id TEXT
            )
        ''')

        # Table: StoryIRBlocks
        await conn.execute('''
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
        ''')
        
        await conn.commit()
