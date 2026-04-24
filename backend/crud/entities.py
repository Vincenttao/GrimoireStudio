from datetime import datetime
from typing import List, Optional

from backend.database import get_db_connection
from backend.models import BaseAttributes, CurrentStatus, Entity, EntityType, VoiceSignature


def _row_to_entity(row) -> Entity:
    """Convert a DB row to an Entity, tolerating legacy rows without voice_signature column."""
    voice_signature = None
    try:
        row_keys = row.keys()
        if "voice_signature_json" in row_keys and row["voice_signature_json"]:
            voice_signature = VoiceSignature.model_validate_json(row["voice_signature_json"])
    except (KeyError, IndexError):
        pass

    return Entity(
        entity_id=row["entity_id"],
        type=EntityType(row["type"]),
        name=row["name"],
        base_attributes=BaseAttributes.model_validate_json(row["base_attributes_json"]),
        current_status=CurrentStatus.model_validate_json(row["current_status_json"]),
        voice_signature=voice_signature,
        is_deleted=bool(row["is_deleted"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


async def create_entity(entity: Entity) -> Entity:
    """Creates a new entity in the database."""
    async with get_db_connection() as conn:
        await conn.execute(
            """
            INSERT INTO entities (
                entity_id, type, name, base_attributes_json,
                current_status_json, voice_signature_json, is_deleted, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity.entity_id,
                entity.type.value,
                entity.name,
                entity.base_attributes.model_dump_json(),
                entity.current_status.model_dump_json(),
                entity.voice_signature.model_dump_json() if entity.voice_signature else None,
                entity.is_deleted,
                entity.created_at.isoformat(),
                entity.updated_at.isoformat(),
            ),
        )
        await conn.commit()
    return entity


async def get_entity(entity_id: str) -> Optional[Entity]:
    """Retrieves an entity by ID."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM entities WHERE entity_id = ? AND is_deleted = 0", (entity_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return _row_to_entity(row)


async def list_entities(type_filter: Optional[str] = None) -> List[Entity]:
    """Lists all active entities, optionally filtered by type."""
    entities = []
    async with get_db_connection() as conn:
        query = "SELECT * FROM entities WHERE is_deleted = 0"
        params = []
        if type_filter:
            query += " AND type = ?"
            params.append(type_filter)

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()

        for row in rows:
            entities.append(_row_to_entity(row))
    return entities


async def update_entity(entity_id: str, update_data: dict) -> Optional[Entity]:
    """Updates specific fields of an entity."""
    existing = await get_entity(entity_id)
    if not existing:
        return None

    updated_dict = existing.model_dump()
    for k, v in update_data.items():
        if k in updated_dict and k != "entity_id":
            updated_dict[k] = v

    updated_dict["updated_at"] = datetime.utcnow()
    new_entity = Entity.model_validate(updated_dict)

    async with get_db_connection() as conn:
        await conn.execute(
            """
            UPDATE entities
            SET type = ?, name = ?, base_attributes_json = ?, current_status_json = ?,
                voice_signature_json = ?, updated_at = ?
            WHERE entity_id = ?
            """,
            (
                new_entity.type.value,
                new_entity.name,
                new_entity.base_attributes.model_dump_json(),
                new_entity.current_status.model_dump_json(),
                new_entity.voice_signature.model_dump_json()
                if new_entity.voice_signature
                else None,
                new_entity.updated_at.isoformat(),
                entity_id,
            ),
        )
        await conn.commit()
    return new_entity


async def soft_delete_entity(entity_id: str) -> bool:
    """Sets is_deleted to True according to SPEC soft delete rules."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "UPDATE entities SET is_deleted = 1, updated_at = ? WHERE entity_id = ?",
            (datetime.utcnow().isoformat(), entity_id),
        )
        await conn.commit()
        return cursor.rowcount > 0
