import pytest
import os
from backend.database import get_db_connection, init_db, DB_PATH

@pytest.mark.asyncio
async def test_database_initialization():
    """
    Test Phase 1.1: Ensure the database can be initialized without errors.
    """
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    await init_db()
    assert os.path.exists(DB_PATH)

@pytest.mark.asyncio
async def test_database_connection_and_wal():
    """
    Test Phase 1.2: Ensure the AGENT.md Strict Mutex constraints and SPEC.md WAL pragma are applied.
    """
    async with get_db_connection() as conn:
        # Check if the connection is alive by running a simple query
        cursor = await conn.execute("SELECT 1")
        result = await cursor.fetchone()
        assert result[0] == 1
        
        # Verify that WAL (Write-Ahead Logging) mode is activated to prevent Database Locked errors
        cursor = await conn.execute("PRAGMA journal_mode;")
        journal_mode = await cursor.fetchone()
        assert journal_mode[0].lower() == "wal", "Database MUST be in WAL mode as per SPEC.md!"
