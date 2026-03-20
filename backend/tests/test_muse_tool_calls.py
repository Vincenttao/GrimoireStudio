"""
TDD Tests for Muse Tool Call functionality.
Tests both unit logic (mocked) and integration (real LLM).

Per SPEC §5.4:
- update_entity: {entity_id, updates}
- delete_entity: {entity_id}
- query_memory: {query}
"""

import os
import pytest
import pytest_asyncio
import re
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from backend.database import DB_PATH, init_db, get_db_connection
from backend.main import app
from backend.models import Entity, EntityType, BaseAttributes, CurrentStatus
from backend.crud.entities import (
    create_entity,
    get_entity,
    soft_delete_entity,
    update_entity,
    list_entities,
)


# ==========================================
# Test Fixtures
# ==========================================


@pytest_asyncio.fixture(autouse=True)
async def db_setup():
    """Ensure a clean database for each test."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    await init_db()
    yield


@pytest.fixture
def sample_entity() -> Entity:
    return Entity(
        entity_id="char_test001",
        type=EntityType.CHARACTER,
        name="测试角色",
        base_attributes=BaseAttributes(
            aliases=["小测"],
            personality="勇敢正直",
            core_motive="寻找真相",
            background="来自北方小村",
        ),
        current_status=CurrentStatus(
            health="良好",
            inventory=["长剑", "盾牌"],
            recent_memory_summary=["击败了山贼", "救了村民"],
            relationships={},
        ),
        is_deleted=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


# ==========================================
# Unit Tests: Tool Call Parsing
# ==========================================


class TestToolCallParsing:
    """Test regex parsing of tool_call code blocks."""

    TOOL_CALL_PATTERN = re.compile(r"```tool_call\n([\s\S]*?)\n```")

    def test_parse_create_entity(self):
        """Test parsing create_entity tool call."""
        content = """好的，我来创建一个角色。
```tool_call
{
  "action": "create_entity",
  "payload": {
    "type": "CHARACTER",
    "name": "李逍遥",
    "base_attributes": {
      "aliases": ["逍遥"],
      "personality": "潇洒不羁",
      "core_motive": "寻找父亲",
      "background": "客栈老板之子"
    }
  }
}
```
请确认是否创建。"""

        match = self.TOOL_CALL_PATTERN.search(content)
        assert match is not None

        import json

        tool_call = json.loads(match.group(1))
        assert tool_call["action"] == "create_entity"
        assert tool_call["payload"]["name"] == "李逍遥"

    def test_parse_update_entity(self):
        """Test parsing update_entity tool call."""
        content = """我来修改这个角色。
```tool_call
{
  "action": "update_entity",
  "payload": {
    "entity_id": "char_test001",
    "updates": {
      "name": "李逍遥·改",
      "current_status": {
        "health": "受伤"
      }
    }
  }
}
```"""

        match = self.TOOL_CALL_PATTERN.search(content)
        assert match is not None

        import json

        tool_call = json.loads(match.group(1))
        assert tool_call["action"] == "update_entity"
        assert tool_call["payload"]["entity_id"] == "char_test001"

    def test_parse_delete_entity(self):
        """Test parsing delete_entity tool call."""
        content = """```tool_call
{
  "action": "delete_entity",
  "payload": {
    "entity_id": "char_test001"
  }
}
```"""

        match = self.TOOL_CALL_PATTERN.search(content)
        assert match is not None

        import json

        tool_call = json.loads(match.group(1))
        assert tool_call["action"] == "delete_entity"
        assert tool_call["payload"]["entity_id"] == "char_test001"

    def test_parse_query_memory(self):
        """Test parsing query_memory tool call."""
        content = """让我查询一下世界状态。
```tool_call
{
  "action": "query_memory",
  "payload": {
    "query": "所有角色的记忆"
  }
}
```"""

        match = self.TOOL_CALL_PATTERN.search(content)
        assert match is not None

        import json

        tool_call = json.loads(match.group(1))
        assert tool_call["action"] == "query_memory"


# ==========================================
# V2.0 Tool Call Parsing Tests
# ==========================================


class TestV2ToolCallParsing:
    """Test parsing of V2.0 tool calls: override_turn, adjust_render, create_branch, rollback."""

    TOOL_CALL_PATTERN = re.compile(r"```tool_call\n([\s\S]*?)\n```")

    def test_parse_override_turn(self):
        """Test parsing override_turn tool call."""
        content = """我想干预这个角色的行动。
```tool_call
{
  "action": "override_turn",
  "payload": {
    "spark_id": "spark_abc123",
    "entity_id": "char_test001",
    "directive": "改变态度，表现出愤怒"
  }
}
```"""

        match = self.TOOL_CALL_PATTERN.search(content)
        assert match is not None

        tool_call = json.loads(match.group(1))
        assert tool_call["action"] == "override_turn"
        assert tool_call["payload"]["entity_id"] == "char_test001"
        assert "directive" in tool_call["payload"]

    def test_parse_adjust_render(self):
        """Test parsing adjust_render tool call."""
        content = """```tool_call
{
  "action": "adjust_render",
  "payload": {
    "subtext_ratio": 0.8,
    "style_template": "Literary",
    "pov_type": "FIRST_PERSON"
  }
}
```"""

        match = self.TOOL_CALL_PATTERN.search(content)
        assert match is not None

        tool_call = json.loads(match.group(1))
        assert tool_call["action"] == "adjust_render"
        assert tool_call["payload"]["subtext_ratio"] == 0.8
        assert tool_call["payload"]["style_template"] == "Literary"

    def test_parse_create_branch(self):
        """Test parsing create_branch tool call."""
        content = """我想创建一个平行分支。
```tool_call
{
  "action": "create_branch",
  "payload": {
    "name": "暗黑路线",
    "origin_snapshot_id": "snap_001",
    "parent_branch_id": "main"
  }
}
```"""

        match = self.TOOL_CALL_PATTERN.search(content)
        assert match is not None

        tool_call = json.loads(match.group(1))
        assert tool_call["action"] == "create_branch"
        assert tool_call["payload"]["name"] == "暗黑路线"
        assert tool_call["payload"]["origin_snapshot_id"] == "snap_001"

    def test_parse_rollback(self):
        """Test parsing rollback tool call."""
        content = """回滚到之前的状态。
```tool_call
{
  "action": "rollback",
  "payload": {
    "snapshot_id": "snap_previous"
  }
}
```"""

        match = self.TOOL_CALL_PATTERN.search(content)
        assert match is not None

        tool_call = json.loads(match.group(1))
        assert tool_call["action"] == "rollback"
        assert tool_call["payload"]["snapshot_id"] == "snap_previous"


# ==========================================
# Integration Tests: Entity CRUD Operations
# ==========================================


class TestEntityOperations:
    """Test entity CRUD operations used by tool calls."""

    @pytest.mark.asyncio
    async def test_update_entity_changes_name(self, sample_entity):
        """Test update_entity modifies entity name."""
        await create_entity(sample_entity)
        updated = await update_entity(sample_entity.entity_id, {"name": "新名字"})

        assert updated is not None
        assert updated.name == "新名字"

    @pytest.mark.asyncio
    async def test_update_entity_changes_current_status(self, sample_entity):
        """Test update_entity modifies current_status."""
        await create_entity(sample_entity)
        updated = await update_entity(
            sample_entity.entity_id,
            {
                "current_status": CurrentStatus(
                    health="受伤",
                    inventory=["长剑"],
                    recent_memory_summary=["新记忆"],
                    relationships={},
                )
            },
        )

        assert updated is not None
        assert updated.current_status.health == "受伤"
        assert "新记忆" in updated.current_status.recent_memory_summary

    @pytest.mark.asyncio
    async def test_update_nonexistent_entity_returns_none(self):
        """Test update_entity with invalid ID returns None."""
        result = await update_entity("nonexistent_id", {"name": "test"})
        assert result is None

    @pytest.mark.asyncio
    async def test_soft_delete_entity(self, sample_entity):
        """Test soft_delete_entity sets is_deleted=True."""
        await create_entity(sample_entity)
        success = await soft_delete_entity(sample_entity.entity_id)
        assert success is True

        # Verify entity is soft deleted
        entity = await get_entity(sample_entity.entity_id)
        assert entity is None  # get_entity filters out deleted

    @pytest.mark.asyncio
    async def test_list_entities_returns_active_only(self, sample_entity):
        """Test list_entities excludes soft-deleted entities."""
        await create_entity(sample_entity)

        # Delete one entity
        await soft_delete_entity(sample_entity.entity_id)

        # Create another active entity
        active = Entity(
            entity_id="char_active",
            type=EntityType.CHARACTER,
            name="活跃角色",
            base_attributes=BaseAttributes(
                aliases=[], personality="test", core_motive="test", background="test"
            ),
            current_status=CurrentStatus(
                health="good", inventory=[], recent_memory_summary=[], relationships={}
            ),
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await create_entity(active)

        entities = await list_entities()
        entity_ids = [e.entity_id for e in entities]

        assert "char_active" in entity_ids
        assert "char_test001" not in entity_ids  # Deleted


# ==========================================
# Integration Tests: API Endpoints
# ==========================================


class TestQueryMemoryEndpoint:
    """Test POST /entities/query endpoint for query_memory tool."""

    @pytest.mark.asyncio
    async def test_query_memory_returns_all_entities_with_memories(self, sample_entity):
        """Test query endpoint returns entities with their memories."""
        await create_entity(sample_entity)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/grimoire/entities/query", json={"query": "all"})

        assert response.status_code == 200
        data = response.json()
        assert "entities" in data

        # Find our test entity
        test_entity = next((e for e in data["entities"] if e["entity_id"] == "char_test001"), None)
        assert test_entity is not None
        assert test_entity["name"] == "测试角色"
        assert len(test_entity["current_status"]["recent_memory_summary"]) > 0

    @pytest.mark.asyncio
    async def test_query_memory_empty_grimoire(self):
        """Test query endpoint with no entities."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/grimoire/entities/query", json={"query": "all"})

        assert response.status_code == 200
        data = response.json()
        assert data["entities"] == []


# ==========================================
# V2.0 API Endpoint Tests
# ==========================================


class TestCreateBranchEndpoint:
    """Test POST /sandbox/branch endpoint for create_branch tool."""

    @pytest.mark.asyncio
    async def test_create_branch_with_name_only(self):
        """Test creating a branch with just a name."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/sandbox/branch", json={"name": "测试分支"})

        assert response.status_code == 200
        data = response.json()
        assert "branch" in data
        assert data["branch"]["name"] == "测试分支"
        assert data["branch"]["is_active"] is True
        assert data["message"] == "Branch '测试分支' created successfully."

    @pytest.mark.asyncio
    async def test_create_branch_with_origin_snapshot(self):
        """Test creating a branch from a snapshot."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/sandbox/branch",
                json={"name": "派生分支", "origin_snapshot_id": "snap_001"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["branch"]["origin_snapshot_id"] == "snap_001"

    @pytest.mark.asyncio
    async def test_create_branch_generates_unique_id(self):
        """Test that each branch gets a unique ID."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response1 = await ac.post("/api/v1/sandbox/branch", json={"name": "分支A"})
            response2 = await ac.post("/api/v1/sandbox/branch", json={"name": "分支B"})

        data1 = response1.json()
        data2 = response2.json()
        assert data1["branch"]["branch_id"] != data2["branch"]["branch_id"]


class TestRollbackEndpoint:
    """Test POST /sandbox/rollback endpoint for rollback tool."""

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_snapshot_returns_404(self):
        """Test rollback with invalid snapshot ID returns 404."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/sandbox/rollback", json={"snapshot_id": "nonexistent"}
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_rollback_restores_entities(self, sample_entity):
        """Test rollback restores entities from snapshot."""
        from backend.crud.snapshots import create_snapshot
        from backend.models import GrimoireStateJSON

        # Create initial entity
        await create_entity(sample_entity)

        # Create a snapshot
        snapshot = await create_snapshot(
            snapshot_id="snap_test",
            branch_id="main",
            grimoire_state=GrimoireStateJSON(entities=[sample_entity]),
            triggering_block_id="block_001",
        )

        # Delete the entity
        await soft_delete_entity(sample_entity.entity_id)

        # Rollback to snapshot
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/sandbox/rollback", json={"snapshot_id": "snap_test"})

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_id"] == "snap_test"
        assert data["entities_count"] == 1

        # Verify entity is restored
        restored = await get_entity(sample_entity.entity_id)
        assert restored is not None
        assert restored.name == sample_entity.name


class TestBranchListEndpoint:
    """Test GET /sandbox/branches endpoint."""

    @pytest.mark.asyncio
    async def test_list_branches_empty(self):
        """Test listing branches when none exist."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/sandbox/branches")

        assert response.status_code == 200
        data = response.json()
        assert "branches" in data

    @pytest.mark.asyncio
    async def test_list_branches_returns_created_branches(self):
        """Test listing branches returns created branches."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Create two branches
            await ac.post("/api/v1/sandbox/branch", json={"name": "分支A"})
            await ac.post("/api/v1/sandbox/branch", json={"name": "分支B"})

            # List branches
            response = await ac.get("/api/v1/sandbox/branches")

        assert response.status_code == 200
        data = response.json()
        branch_names = [b["name"] for b in data["branches"]]
        assert "分支A" in branch_names
        assert "分支B" in branch_names


# ==========================================
# LLM Integration Tests (Real API)
# ==========================================


@pytest.mark.llm
class TestMuseLLMIntegration:
    """Integration tests using real LLM API."""

    @pytest.mark.asyncio
    async def test_llm_generates_update_entity_tool_call(self):
        """Test that LLM can generate valid update_entity tool call."""
        import os
        from pathlib import Path
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).parent.parent.parent / ".env")

        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API key configured")

        import litellm

        model = os.getenv("LLM_MODEL", "gpt-4")
        api_base = os.getenv("LLM_API_BASE")

        # For custom base URLs, prefix with openai/
        if api_base and "/" not in model:
            model = f"openai/{model}"

        system_prompt = """你是 The Muse。当用户想要修改角色时，输出以下格式的 tool_call:
```tool_call
{
  "action": "update_entity",
  "payload": {
    "entity_id": "角色ID",
    "updates": {
      "name": "新名字",
      "current_status": {"health": "新状态"}
    }
  }
}
```

当前世界有一个角色：测试角色(char_test001)，状态良好。"""

        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "把测试角色的名字改成'李逍遥'"},
            ],
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=api_base,
            temperature=0.1,
        )

        content = response.choices[0].message.content
        assert content is not None

        # Parse tool call
        match = re.search(r"```tool_call\n([\s\S]*?)\n```", content)
        assert match is not None, f"No tool_call found in: {content}"

        tool_call = json.loads(match.group(1))
        assert tool_call["action"] == "update_entity"
        assert "entity_id" in tool_call["payload"]
        assert "updates" in tool_call["payload"]

    @pytest.mark.asyncio
    async def test_llm_generates_query_memory_tool_call(self):
        """Test that LLM can generate valid query_memory tool call."""
        import os
        from pathlib import Path
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).parent.parent.parent / ".env")

        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API key configured")

        import litellm

        model = os.getenv("LLM_MODEL", "gpt-4")
        api_base = os.getenv("LLM_API_BASE")

        if api_base and "/" not in model:
            model = f"openai/{model}"

        system_prompt = """你是 The Muse。当用户想要查询世界状态时，输出:
```tool_call
{
  "action": "query_memory",
  "payload": {
    "query": "查询内容"
  }
}
```"""

        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "告诉我所有角色的记忆"},
            ],
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=api_base,
            temperature=0.1,
        )

        content = response.choices[0].message.content
        assert content is not None

        match = re.search(r"```tool_call\n([\s\S]*?)\n```", content)
        assert match is not None, f"No tool_call found in: {content}"

        tool_call = json.loads(match.group(1))
        assert tool_call["action"] == "query_memory"

    @pytest.mark.asyncio
    async def test_llm_generates_delete_entity_tool_call(self):
        """Test that LLM can generate valid delete_entity tool call."""
        import os
        from pathlib import Path
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).parent.parent.parent / ".env")

        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API key configured")

        import litellm

        model = os.getenv("LLM_MODEL", "gpt-4")
        api_base = os.getenv("LLM_API_BASE")

        if api_base and "/" not in model:
            model = f"openai/{model}"

        system_prompt = """你是 The Muse。当用户想要删除角色时，输出:
```tool_call
{
  "action": "delete_entity",
  "payload": {
    "entity_id": "要删除的角色ID"
  }
}
```

当前角色：测试角色(char_test001)"""

        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "删除测试角色"},
            ],
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=api_base,
            temperature=0.1,
        )

        content = response.choices[0].message.content
        assert content is not None

        match = re.search(r"```tool_call\n([\s\S]*?)\n```", content)
        assert match is not None, f"No tool_call found in: {content}"

        tool_call = json.loads(match.group(1))
        assert tool_call["action"] == "delete_entity"
        assert "entity_id" in tool_call["payload"]
