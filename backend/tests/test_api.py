import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.models import ActionItem, SceneContext, StoryIRBlock


@pytest.mark.asyncio
async def test_api_health():
    """Test standard health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_spark_endpoint_accepts_valid_payload():
    """Test that POST /sandbox/spark accepts valid TheSpark schema."""
    # Setup: Create an entity first (spark requires non-empty Grimoire)
    entity_id = str(uuid.uuid4())
    entity_payload = {
        "entity_id": entity_id,
        "type": "CHARACTER",
        "name": "Test Character",
        "base_attributes": {
            "aliases": [],
            "personality": "brave",
            "core_motive": "adventure",
            "background": "hero",
        },
        "current_status": {
            "health": "good",
            "inventory": [],
            "recent_memory_summary": [],
            "relationships": {},
        },
        "created_at": "2026-03-11T00:00:00+00:00",
        "updated_at": "2026-03-11T00:00:00+00:00",
    }

    valid_payload = {
        "spark_id": "test-uuid-1",
        "chapter_id": "chap-uuid-1",
        "user_prompt": "Hello Grimoire",
        "overrides": {},
    }

    # Mock the Maestro orchestration to prevent actual LLM calls
    with patch("backend.routers.sandbox.run_maestro_orchestration", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # First create an entity
            await ac.post("/api/v1/grimoire/entities", json=entity_payload)
            # Then trigger spark
            response = await ac.post("/api/v1/sandbox/spark", json=valid_payload)

    # 202 Accepted because it fires async loop
    assert response.status_code == 202
    assert response.json()["message"] == "Accepted"


@pytest.mark.asyncio
async def test_sandbox_state_mock():
    """Test sandbox global state returns."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/sandbox/state")

    assert response.status_code == 200
    assert "state" in response.json()


@pytest.mark.asyncio
async def test_grimoire_entity_soft_delete_placeholder():
    """Test that DELETE entity endpoint exists and works with DB."""
    random_id = str(uuid.uuid4())
    valid_payload = {
        "entity_id": random_id,
        "type": "CHARACTER",
        "name": "Dummy",
        "base_attributes": {
            "aliases": [],
            "personality": "none",
            "core_motive": "none",
            "background": "none",
        },
        "current_status": {
            "health": "none",
            "inventory": [],
            "recent_memory_summary": [],
            "relationships": {},
        },
        "created_at": "2026-03-11T00:00:00+00:00",
        "updated_at": "2026-03-11T00:00:00+00:00",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/grimoire/entities", json=valid_payload)
        response = await ac.delete(f"/api/v1/grimoire/entities/{random_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "soft_deleted"


@pytest.mark.asyncio
async def test_render_endpoint_renders_ir_block():
    """Test that POST /render renders an IR block and returns HTML."""
    from backend.crud.storyboard import create_story_ir_block

    # Create a test IR block
    block_id = str(uuid.uuid4())
    ir_block = StoryIRBlock(
        block_id=block_id,
        chapter_id="chap_001",
        lexorank="a0",
        summary="Test scene",
        involved_entities=[],
        scene_context=SceneContext(location_id="loc_001", time_of_day="day"),
        action_sequence=[
            ActionItem(
                actor_id="SYSTEM",
                intent="test",
                action="A test action",
                dialogue="",
            )
        ],
        created_at=datetime.utcnow(),
    )

    await create_story_ir_block(ir_block)

    render_payload = {
        "ir_block_id": block_id,
        "pov_type": "OMNISCIENT",
        "style_template": "Standard",
        "subtext_ratio": 0.5,
    }

    # Mock the Camera client
    with patch("backend.routers.render.get_camera_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.render.return_value = "<p>Test rendered content</p>"
        mock_get_client.return_value = mock_client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/render", json=render_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["content_html"] == "<p>Test rendered content</p>"


@pytest.mark.asyncio
async def test_render_endpoint_returns_404_for_nonexistent_block():
    """Test that render returns 404 for non-existent IR block."""
    render_payload = {
        "ir_block_id": "nonexistent-block-id",
        "pov_type": "OMNISCIENT",
        "style_template": "Standard",
        "subtext_ratio": 0.5,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/render", json=render_payload)

    assert response.status_code == 404
