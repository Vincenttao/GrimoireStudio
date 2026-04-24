"""
CRUD operations for Branch entities.
Per PRD §3.3 - Branching Tree UI with lazy snapshot.
"""

from datetime import datetime
from typing import List, Optional

from backend.database import get_db_connection
from backend.models import Branch


async def create_branch(
    branch_id: str,
    name: str,
    origin_snapshot_id: Optional[str] = None,
    parent_branch_id: Optional[str] = None,
) -> Branch:
    """
    Creates a new branch in the database.

    Args:
        branch_id: Unique identifier for the branch
        name: Human-readable branch name
        origin_snapshot_id: Optional snapshot this branch originated from
        parent_branch_id: Optional parent branch ID

    Returns:
        The created Branch object
    """
    now = datetime.utcnow()

    async with get_db_connection() as conn:
        await conn.execute(
            """
            INSERT INTO branches (branch_id, name, origin_snapshot_id, parent_branch_id, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (branch_id, name, origin_snapshot_id, parent_branch_id, True, now.isoformat()),
        )
        await conn.commit()

    return Branch(
        branch_id=branch_id,
        name=name,
        origin_snapshot_id=origin_snapshot_id,
        parent_branch_id=parent_branch_id,
        is_active=True,
        created_at=now,
    )


async def get_branch(branch_id: str) -> Optional[Branch]:
    """
    Retrieves a branch by ID.

    Args:
        branch_id: The branch ID to look up

    Returns:
        Branch object if found, None otherwise
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM branches WHERE branch_id = ?",
            (branch_id,),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return Branch(
            branch_id=row["branch_id"],
            name=row["name"],
            origin_snapshot_id=row["origin_snapshot_id"],
            parent_branch_id=row["parent_branch_id"],
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


async def list_branches(active_only: bool = True) -> List[Branch]:
    """
    Lists all branches.

    Args:
        active_only: If True, only return active branches

    Returns:
        List of Branch objects
    """
    branches = []

    async with get_db_connection() as conn:
        if active_only:
            cursor = await conn.execute(
                "SELECT * FROM branches WHERE is_active = 1 ORDER BY created_at DESC"
            )
        else:
            cursor = await conn.execute("SELECT * FROM branches ORDER BY created_at DESC")

        rows = await cursor.fetchall()

        for row in rows:
            branches.append(
                Branch(
                    branch_id=row["branch_id"],
                    name=row["name"],
                    origin_snapshot_id=row["origin_snapshot_id"],
                    parent_branch_id=row["parent_branch_id"],
                    is_active=bool(row["is_active"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )

    return branches


async def deactivate_branch(branch_id: str) -> bool:
    """
    Deactivates a branch (soft delete).

    Args:
        branch_id: The branch ID to deactivate

    Returns:
        True if branch was deactivated, False if not found
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "UPDATE branches SET is_active = 0 WHERE branch_id = ?",
            (branch_id,),
        )
        await conn.commit()
        return cursor.rowcount > 0


async def update_branch_name(branch_id: str, new_name: str) -> Optional[Branch]:
    """
    Updates a branch's name.

    Args:
        branch_id: The branch ID to update
        new_name: The new name for the branch

    Returns:
        Updated Branch object if found, None otherwise
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "UPDATE branches SET name = ? WHERE branch_id = ?",
            (new_name, branch_id),
        )
        await conn.commit()

        if cursor.rowcount == 0:
            return None

    return await get_branch(branch_id)
