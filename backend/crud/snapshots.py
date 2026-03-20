"""
CRUD operations for Snapshot entities.
Per PRD §3.3 - Rollback to snapshot.
"""

from datetime import datetime
from typing import Optional, List
import aiosqlite

from backend.models import GrimoireSnapshot, GrimoireStateJSON
from backend.database import get_db_connection


async def create_snapshot(
    snapshot_id: str,
    branch_id: str,
    grimoire_state: GrimoireStateJSON,
    triggering_block_id: str,
    parent_snapshot_id: Optional[str] = None,
) -> GrimoireSnapshot:
    """
    Creates a new snapshot in the database.

    Args:
        snapshot_id: Unique identifier for the snapshot
        branch_id: The branch this snapshot belongs to
        grimoire_state: The world state to capture
        triggering_block_id: The IR block that triggered this snapshot
        parent_snapshot_id: Optional parent snapshot for history chain

    Returns:
        The created GrimoireSnapshot object
    """
    now = datetime.utcnow()

    async with get_db_connection() as conn:
        await conn.execute(
            """
            INSERT INTO snapshots (snapshot_id, branch_id, parent_snapshot_id, triggering_block_id, grimoire_state_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                branch_id,
                parent_snapshot_id,
                triggering_block_id,
                grimoire_state.model_dump_json(),
                now.isoformat(),
            ),
        )
        await conn.commit()

    return GrimoireSnapshot(
        snapshot_id=snapshot_id,
        branch_id=branch_id,
        parent_snapshot_id=parent_snapshot_id,
        triggering_block_id=triggering_block_id,
        grimoire_state_json=grimoire_state,
        created_at=now,
    )


async def get_snapshot(snapshot_id: str) -> Optional[GrimoireSnapshot]:
    """
    Retrieves a snapshot by ID.

    Args:
        snapshot_id: The snapshot ID to look up

    Returns:
        GrimoireSnapshot object if found, None otherwise
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM snapshots WHERE snapshot_id = ?",
            (snapshot_id,),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return GrimoireSnapshot(
            snapshot_id=row["snapshot_id"],
            branch_id=row["branch_id"],
            parent_snapshot_id=row["parent_snapshot_id"],
            triggering_block_id=row["triggering_block_id"],
            grimoire_state_json=GrimoireStateJSON.model_validate_json(row["grimoire_state_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


async def get_latest_snapshot(branch_id: str) -> Optional[GrimoireSnapshot]:
    """
    Gets the most recent snapshot for a branch.

    Args:
        branch_id: The branch to get the latest snapshot for

    Returns:
        The most recent GrimoireSnapshot for the branch, or None if no snapshots exist
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT * FROM snapshots 
            WHERE branch_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
            """,
            (branch_id,),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return GrimoireSnapshot(
            snapshot_id=row["snapshot_id"],
            branch_id=row["branch_id"],
            parent_snapshot_id=row["parent_snapshot_id"],
            triggering_block_id=row["triggering_block_id"],
            grimoire_state_json=GrimoireStateJSON.model_validate_json(row["grimoire_state_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


async def list_snapshots_by_branch(branch_id: str) -> List[GrimoireSnapshot]:
    """
    Lists all snapshots for a branch.

    Args:
        branch_id: The branch to list snapshots for

    Returns:
        List of GrimoireSnapshot objects, ordered by creation time (newest first)
    """
    snapshots = []

    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT * FROM snapshots 
            WHERE branch_id = ? 
            ORDER BY created_at DESC
            """,
            (branch_id,),
        )
        rows = await cursor.fetchall()

        for row in rows:
            snapshots.append(
                GrimoireSnapshot(
                    snapshot_id=row["snapshot_id"],
                    branch_id=row["branch_id"],
                    parent_snapshot_id=row["parent_snapshot_id"],
                    triggering_block_id=row["triggering_block_id"],
                    grimoire_state_json=GrimoireStateJSON.model_validate_json(
                        row["grimoire_state_json"]
                    ),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )

    return snapshots


async def list_all_snapshots() -> List[GrimoireSnapshot]:
    """
    Lists all snapshots in the database.

    Returns:
        List of all GrimoireSnapshot objects, ordered by creation time (newest first)
    """
    snapshots = []

    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM snapshots ORDER BY created_at DESC")
        rows = await cursor.fetchall()

        for row in rows:
            snapshots.append(
                GrimoireSnapshot(
                    snapshot_id=row["snapshot_id"],
                    branch_id=row["branch_id"],
                    parent_snapshot_id=row["parent_snapshot_id"],
                    triggering_block_id=row["triggering_block_id"],
                    grimoire_state_json=GrimoireStateJSON.model_validate_json(
                        row["grimoire_state_json"]
                    ),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )

    return snapshots
