import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

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
    valid_payload = {
        "spark_id": "test-uuid-1",
        "chapter_id": "chap-uuid-1",
        "user_prompt": "Hello Grimoire",
        "overrides": {}
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
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

import uuid

@pytest.mark.asyncio
async def test_grimoire_entity_soft_delete_placeholder():
    """Test that DELETE entity endpoint exists and works with DB."""
    random_id = str(uuid.uuid4())
    valid_payload = {
        "entity_id": random_id,
        "type": "CHARACTER",
        "name": "Dummy",
        "base_attributes": {"aliases": [], "personality": "none", "core_motive": "none", "background": "none"},
        "current_status": {"health": "none", "inventory": [], "recent_memory_summary": [], "relationships": {}},
        "created_at": "2026-03-11T00:00:00+00:00",
        "updated_at": "2026-03-11T00:00:00+00:00"
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/grimoire/entities", json=valid_payload)
        response = await ac.delete(f"/api/v1/grimoire/entities/{random_id}")
        
    assert response.status_code == 200
    assert response.json()["status"] == "soft_deleted"
