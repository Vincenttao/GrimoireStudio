"""
V1.1 SoftPatch CRUD — 作者手动事实修订的软层 delta。

不改历史快照，只在当前 Grimoire 指针上 overlay。
下次 Commit 时合并进新快照，打标 merged_into_snapshot_id。
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional

from backend.database import get_db_connection
from backend.models import SoftPatch, SoftPatchStatus


async def create_soft_patch(
    target_entity_id: str,
    target_path: str,
    old_value,
    new_value,
    author_note: str,
) -> SoftPatch:
    """Create a pending SoftPatch."""
    patch = SoftPatch(
        patch_id=f"patch_{uuid.uuid4().hex[:12]}",
        target_entity_id=target_entity_id,
        target_path=target_path,
        old_value=old_value,
        new_value=new_value,
        author_note=author_note,
        status=SoftPatchStatus.PENDING,
        created_at=datetime.utcnow(),
    )

    async with get_db_connection() as conn:
        await conn.execute(
            """INSERT INTO soft_patches (
                patch_id, target_entity_id, target_path,
                old_value_json, new_value_json, author_note,
                status, created_at, merged_into_snapshot_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                patch.patch_id,
                patch.target_entity_id,
                patch.target_path,
                json.dumps(patch.old_value, ensure_ascii=False),
                json.dumps(patch.new_value, ensure_ascii=False),
                patch.author_note,
                patch.status.value,
                patch.created_at.isoformat(),
                patch.merged_into_snapshot_id,
            ),
        )
        await conn.commit()

    return patch


def _row_to_patch(row) -> SoftPatch:
    return SoftPatch(
        patch_id=row["patch_id"],
        target_entity_id=row["target_entity_id"],
        target_path=row["target_path"],
        old_value=json.loads(row["old_value_json"]),
        new_value=json.loads(row["new_value_json"]),
        author_note=row["author_note"],
        status=SoftPatchStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        merged_into_snapshot_id=row["merged_into_snapshot_id"],
    )


async def list_pending_patches(entity_id: Optional[str] = None) -> List[SoftPatch]:
    """Get all PENDING soft patches, optionally filtered by entity."""
    async with get_db_connection() as conn:
        if entity_id:
            cursor = await conn.execute(
                "SELECT * FROM soft_patches WHERE status = 'PENDING' AND target_entity_id = ? ORDER BY created_at",
                (entity_id,),
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM soft_patches WHERE status = 'PENDING' ORDER BY created_at"
            )
        rows = await cursor.fetchall()
        return [_row_to_patch(r) for r in rows]


async def get_patch(patch_id: str) -> Optional[SoftPatch]:
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM soft_patches WHERE patch_id = ?", (patch_id,))
        row = await cursor.fetchone()
        return _row_to_patch(row) if row else None


async def discard_patch(patch_id: str) -> bool:
    """Discard a pending patch (user undo before commit)."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "UPDATE soft_patches SET status = 'DISCARDED' WHERE patch_id = ? AND status = 'PENDING'",
            (patch_id,),
        )
        await conn.commit()
        return cursor.rowcount > 0


async def mark_merged(patch_ids: List[str], snapshot_id: str) -> int:
    """Mark patches as merged into a snapshot. Called at Commit time."""
    if not patch_ids:
        return 0
    async with get_db_connection() as conn:
        placeholders = ",".join(["?"] * len(patch_ids))
        cursor = await conn.execute(
            f"""UPDATE soft_patches
                SET status = 'MERGED', merged_into_snapshot_id = ?
                WHERE patch_id IN ({placeholders})""",
            [snapshot_id, *patch_ids],
        )
        await conn.commit()
        return cursor.rowcount


def apply_patch_to_dict(data: dict, target_path: str, new_value) -> dict:
    """
    Overlay a SoftPatch onto a dict in memory. target_path is a simple dot-path
    like "current_status.inventory" or "base_attributes.personality".

    Returns a new dict (does not mutate input).
    """
    import copy

    result = copy.deepcopy(data)
    parts = target_path.split(".")
    cursor = result
    for p in parts[:-1]:
        if p not in cursor or not isinstance(cursor[p], dict):
            cursor[p] = {}
        cursor = cursor[p]
    cursor[parts[-1]] = new_value
    return result
