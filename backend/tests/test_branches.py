"""
TDD Tests for Branch CRUD operations.
Per PRD §3.3 - Branching Tree UI with lazy snapshot.
"""

import os

import pytest
import pytest_asyncio

from backend.crud.branches import (
    create_branch,
    deactivate_branch,
    get_branch,
    list_branches,
)
from backend.database import DB_PATH, init_db


@pytest_asyncio.fixture(autouse=True)
async def db_setup():
    """Ensure a clean database for each test."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    await init_db()
    yield


class TestBranchCRUD:
    """Test branch CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_branch_with_custom_id(self):
        """Test creating a branch with a custom ID."""
        branch = await create_branch(
            branch_id="branch-001",
            name="Main Timeline",
            origin_snapshot_id=None,
        )

        assert branch is not None
        assert branch.branch_id == "branch-001"
        assert branch.name == "Main Timeline"
        assert branch.origin_snapshot_id is None
        assert branch.is_active is True

    @pytest.mark.asyncio
    async def test_create_branch_with_origin_snapshot(self):
        """Test creating a branch from a snapshot."""
        branch = await create_branch(
            branch_id="branch-002",
            name="Parallel Universe",
            origin_snapshot_id="snap-001",
        )

        assert branch.origin_snapshot_id == "snap-001"

    @pytest.mark.asyncio
    async def test_get_branch_by_id(self):
        """Test retrieving a branch by ID."""
        await create_branch(
            branch_id="branch-003",
            name="Test Branch",
            origin_snapshot_id=None,
        )

        branch = await get_branch("branch-003")

        assert branch is not None
        assert branch.name == "Test Branch"

    @pytest.mark.asyncio
    async def test_get_branch_not_found(self):
        """Test retrieving a non-existent branch."""
        branch = await get_branch("nonexistent")
        assert branch is None

    @pytest.mark.asyncio
    async def test_list_branches_empty(self):
        """Test listing branches when empty."""
        branches = await list_branches()
        assert branches == []

    @pytest.mark.asyncio
    async def test_list_branches_returns_all(self):
        """Test listing all branches."""
        await create_branch("branch-a", "Branch A", None)
        await create_branch("branch-b", "Branch B", None)

        branches = await list_branches()

        assert len(branches) == 2
        names = [b.name for b in branches]
        assert "Branch A" in names
        assert "Branch B" in names

    @pytest.mark.asyncio
    async def test_list_branches_excludes_inactive(self):
        """Test that inactive branches are excluded by default."""
        await create_branch("branch-active", "Active", None)
        await create_branch("branch-inactive", "Inactive", None)
        await deactivate_branch("branch-inactive")

        branches = await list_branches()

        assert len(branches) == 1
        assert branches[0].name == "Active"

    @pytest.mark.asyncio
    async def test_deactivate_branch(self):
        """Test deactivating a branch."""
        await create_branch("branch-to-deactivate", "To Deactivate", None)

        success = await deactivate_branch("branch-to-deactivate")

        assert success is True

        # Verify it's deactivated
        branch = await get_branch("branch-to-deactivate")
        assert branch.is_active is False

    @pytest.mark.asyncio
    async def test_deactivate_nonexistent_branch(self):
        """Test deactivating a non-existent branch."""
        success = await deactivate_branch("nonexistent")
        assert success is False
