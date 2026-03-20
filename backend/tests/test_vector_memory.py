import asyncio

import pytest

from backend.crud.memory import delete_memories_by_entity, insert_memory, search_memories
from backend.database import init_db


@pytest.fixture(scope="module")
def setup_database():
    """Initialize the database for testing"""
    asyncio.run(init_db())


@pytest.mark.asyncio
async def test_table_creation(setup_database):
    """Test if memory_vectors table is correctly created"""
    from backend.database import get_db_connection

    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_vectors';"
        )
        row = await cursor.fetchone()
        assert row is not None, "memory_vectors table not found"
        assert row[0] == "memory_vectors", "Incorrect table name"


@pytest.mark.asyncio
async def test_insert_memory(setup_database):
    """Test inserting a memory and getting an ID back"""
    # Insert a test memory
    memory_id = await insert_memory("test_entity_1", "This is a sample memory for testing purposes")

    # Verify we got an integer ID back
    assert isinstance(memory_id, int), "insert_memory should return an integer ID"
    assert memory_id > 0, "insert_memory should return a positive integer ID"


@pytest.mark.asyncio
async def test_search_memories_by_entity(setup_database):
    """Test searching memories by entity"""
    # Insert some test memories first
    entity_id = "test_entity_2"
    await insert_memory(entity_id, "This is about cats and dogs playing together")
    await insert_memory(entity_id, "This discusses quantum physics concepts")
    await insert_memory("different_entity", "This should not appear in entity-specific search")

    # Test search within specific entity
    results = await search_memories("animals playing", entity_id=entity_id, top_k=5)

    # We expect at least one result and they should be from the correct entity
    assert len(results) > 0, "Should find memories within the specified entity"
    for result in results:
        assert result["entity_id"] == entity_id, "All results should belong to the specified entity"


@pytest.mark.asyncio
async def test_search_memories_all_entities(setup_database):
    """Test searching memories across all entities"""
    # Insert two different types of memories
    entity1_id = "test_entity_3"
    entity2_id = "test_entity_4"

    await insert_memory(
        entity1_id, "Memory related to artificial intelligence and machine learning"
    )
    await insert_memory(entity2_id, "Memory related to cooking and baking recipes")

    # Search for a general topic across all entities
    results = await search_memories("technology and systems", entity_id=None, top_k=10)

    # Should return results from different or various entities based on semantic similarity
    assert len(results) > 0, "Should find memories across entities when searched globally"


@pytest.mark.asyncio
async def test_delete_memories_by_entity(setup_database):
    """Test deleting memories by entity"""
    # Insert some memories to delete
    test_entity = "test_entity_to_delete"
    await insert_memory(test_entity, "First memory to be deleted")
    await insert_memory(test_entity, "Second memory to be deleted")
    await insert_memory("preserve_this_entity", "This memory should be preserved")

    # Verify that we have memories associated with our test entity
    search_before = await search_memories("deleted", entity_id=test_entity, top_k=10)
    assert len(search_before) >= 2, "There should be memories to delete"

    # Delete memories belonging to the test entity
    deleted_count = await delete_memories_by_entity(test_entity)
    assert deleted_count >= 2, "Should have deleted at least the two inserted memories"

    # Verify that memories from that entity are gone but others remain
    search_after = await search_memories("deleted", entity_id=test_entity, top_k=10)
    assert len(search_after) == 0, "Should have no memories from deleted entity"

    # Check that other entities weren't affected
    remaining_memories = await search_memories(
        "preserved", entity_id="preserve_this_entity", top_k=10
    )
    assert len(remaining_memories) > 0, "Memories from other entities should still exist"
