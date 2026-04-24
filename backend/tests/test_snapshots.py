"""
TDD Tests for Snapshot CRUD operations.
Per PRD §3.3 - Rollback to snapshot.
"""

import os
from datetime import datetime

import pytest
import pytest_asyncio

from backend.crud.branches import create_branch
from backend.crud.snapshots import (
    create_snapshot,
    get_latest_snapshot,
    get_snapshot,
    list_snapshots_by_branch,
)
from backend.database import DB_PATH, init_db
from backend.models import (
    BaseAttributes,
    CurrentStatus,
    Entity,
    EntityType,
    GrimoireStateJSON,
)


@pytest_asyncio.fixture(autouse=True)
async def db_setup():
    """Ensure a clean database for each test."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    await init_db()
    yield


class TestSnapshotCRUD:
    """Test snapshot CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_snapshot(self):
        """Test creating a snapshot."""
        # Create a branch first
        await create_branch("branch-001", "Main", None)

        state = GrimoireStateJSON(entities=[])
        snapshot = await create_snapshot(
            snapshot_id="snap-001",
            branch_id="branch-001",
            grimoire_state=state,
            triggering_block_id="block-001",
        )

        assert snapshot is not None
        assert snapshot.snapshot_id == "snap-001"
        assert snapshot.branch_id == "branch-001"
        assert snapshot.triggering_block_id == "block-001"
        assert len(snapshot.grimoire_state_json.entities) == 0

    @pytest.mark.asyncio
    async def test_create_snapshot_with_entities(self):
        """Test creating a snapshot with entity state."""
        await create_branch("branch-002", "Test", None)

        entity = Entity(
            entity_id="char-001",
            type=EntityType.CHARACTER,
            name="Test Character",
            base_attributes=BaseAttributes(
                personality="brave",
                core_motive="adventure",
                background="hero",
            ),
            current_status=CurrentStatus(health="good"),
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        state = GrimoireStateJSON(entities=[entity])
        snapshot = await create_snapshot(
            snapshot_id="snap-002",
            branch_id="branch-002",
            grimoire_state=state,
            triggering_block_id="block-002",
        )

        assert len(snapshot.grimoire_state_json.entities) == 1
        assert snapshot.grimoire_state_json.entities[0].name == "Test Character"

    @pytest.mark.asyncio
    async def test_create_snapshot_with_parent(self):
        """Test creating a snapshot with a parent snapshot."""
        await create_branch("branch-003", "Test", None)

        state = GrimoireStateJSON(entities=[])

        # Create parent snapshot
        await create_snapshot(
            snapshot_id="snap-parent",
            branch_id="branch-003",
            grimoire_state=state,
            triggering_block_id="block-001",
        )

        # Create child snapshot
        child = await create_snapshot(
            snapshot_id="snap-child",
            branch_id="branch-003",
            grimoire_state=state,
            triggering_block_id="block-002",
            parent_snapshot_id="snap-parent",
        )

        assert child.parent_snapshot_id == "snap-parent"

    @pytest.mark.asyncio
    async def test_get_snapshot_by_id(self):
        """Test retrieving a snapshot by ID."""
        await create_branch("branch-004", "Test", None)

        state = GrimoireStateJSON(entities=[])
        await create_snapshot(
            snapshot_id="snap-004",
            branch_id="branch-004",
            grimoire_state=state,
            triggering_block_id="block-001",
        )

        snapshot = await get_snapshot("snap-004")

        assert snapshot is not None
        assert snapshot.snapshot_id == "snap-004"

    @pytest.mark.asyncio
    async def test_get_snapshot_not_found(self):
        """Test retrieving a non-existent snapshot."""
        snapshot = await get_snapshot("nonexistent")
        assert snapshot is None

    @pytest.mark.asyncio
    async def test_get_latest_snapshot(self):
        """Test getting the latest snapshot for a branch."""
        await create_branch("branch-005", "Test", None)

        state = GrimoireStateJSON(entities=[])

        # Create multiple snapshots
        await create_snapshot("snap-old", "branch-005", state, "block-001")
        await create_snapshot("snap-new", "branch-005", state, "block-002")

        latest = await get_latest_snapshot("branch-005")

        assert latest is not None
        assert latest.snapshot_id == "snap-new"

    @pytest.mark.asyncio
    async def test_get_latest_snapshot_no_snapshots(self):
        """Test getting latest snapshot when none exist."""
        await create_branch("branch-006", "Test", None)

        latest = await get_latest_snapshot("branch-006")
        assert latest is None

    @pytest.mark.asyncio
    async def test_list_snapshots_by_branch(self):
        """Test listing snapshots for a branch."""
        await create_branch("branch-a", "Branch A", None)
        await create_branch("branch-b", "Branch B", None)

        state = GrimoireStateJSON(entities=[])

        # Create snapshots for both branches
        await create_snapshot("snap-a1", "branch-a", state, "block-001")
        await create_snapshot("snap-a2", "branch-a", state, "block-002")
        await create_snapshot("snap-b1", "branch-b", state, "block-003")

        snapshots_a = await list_snapshots_by_branch("branch-a")
        snapshots_b = await list_snapshots_by_branch("branch-b")

        assert len(snapshots_a) == 2
        assert len(snapshots_b) == 1

        ids_a = [s.snapshot_id for s in snapshots_a]
        assert "snap-a1" in ids_a
        assert "snap-a2" in ids_a
