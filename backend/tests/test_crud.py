import pytest
import os
import asyncio
from datetime import datetime

from backend.database import DB_PATH, init_db, get_db_connection
from backend.models import (
    Entity, EntityType, BaseAttributes, CurrentStatus,
    ScribeExtractionResult, DeltaUpdate, ScribeMemoryDelta, InventoryChanges,
    GrimoireSnapshot, GrimoireStateJSON
)
from backend.crud.entities import create_entity, get_entity
from backend.crud.scribe import ScribeApplier

import pytest_asyncio

@pytest_asyncio.fixture(autouse=True)
async def db_setup():
    """Ensure a clean database for each test."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    await init_db()
    yield

@pytest.mark.asyncio
async def test_entity_crud_lifecycle():
    """Test full create/read cycle for a Grimoire Entity."""
    ent_id = "test-char-1"
    entity = Entity(
        entity_id=ent_id,
        type=EntityType.CHARACTER,
        name="Lira",
        base_attributes=BaseAttributes(personality="Brave", core_motive="Escape", background="Thief"),
        current_status=CurrentStatus(health="100/100"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # 1. Create
    await create_entity(entity)
    
    # 2. Read
    fetched = await get_entity(ent_id)
    assert fetched is not None
    assert fetched.name == "Lira"
    assert fetched.base_attributes.personality == "Brave"
    assert fetched.current_status.health == "100/100"

@pytest.mark.asyncio
async def test_scribe_delta_application():
    """Test Phase 5: Ensure Scribe Applier mutates the deep snapshot correctly."""
    
    # 1. Setup Base Snapshot
    ent_id = "target_x"
    base_entity = Entity(
        entity_id=ent_id,
        type=EntityType.CHARACTER,
        name="Hero",
        base_attributes=BaseAttributes(personality="", core_motive="", background=""),
        current_status=CurrentStatus(
            health="Good",
            inventory=["Sword"],
            relationships={"villain1": "Hate"},
            recent_memory_summary=[]
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    snapshot = GrimoireSnapshot(
        snapshot_id="snap1",
        branch_id="main",
        parent_snapshot_id=None,
        triggering_block_id="block0",
        grimoire_state_json=GrimoireStateJSON(entities=[base_entity]),
        created_at=datetime.utcnow()
    )
    
    # 2. Setup Scribe Delta
    delta_result = ScribeExtractionResult(
        updates=[
            DeltaUpdate(
                entity_id=ent_id,
                delta=ScribeMemoryDelta(
                    inventory_changes=InventoryChanges(added=["Shield"], removed=["Sword"]),
                    health_delta="Wounded",
                    memory_to_append="I found a shield but lost my sword.",
                    relationship_changes={"villain1": "Mortal Enemy"}
                )
            )
        ]
    )
    
    # 3. Apply Delta
    new_snapshot = ScribeApplier.apply_delta(snapshot, delta_result, max_memory_items=5)
    
    # 4. Assertions on the new independent state
    updated_entity = new_snapshot.grimoire_state_json.entities[0]
    assert updated_entity.current_status.health == "Wounded"
    assert "Shield" in updated_entity.current_status.inventory
    assert "Sword" not in updated_entity.current_status.inventory
    assert updated_entity.current_status.relationships["villain1"] == "Mortal Enemy"
    assert len(updated_entity.current_status.recent_memory_summary) == 1
    assert "found a shield" in updated_entity.current_status.recent_memory_summary[0]
