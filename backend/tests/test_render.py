"""
Tests for Render API endpoints.
Includes tests for /render/adjust endpoint for V2.0.
"""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.database import DB_PATH, init_db
from backend.main import app

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


# ==========================================
# Tests: /render/adjust Endpoint
# ==========================================


class TestAdjustRenderEndpoint:
    """Test POST /api/v1/render/adjust endpoint."""

    @pytest.mark.asyncio
    async def test_adjust_subtext_ratio(self):
        """Test adjusting subtext_ratio parameter."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/render/adjust", json={"subtext_ratio": 0.75})

        assert response.status_code == 200
        data = response.json()
        assert "default_render_mixer" in data
        assert data["default_render_mixer"]["subtext_ratio"] == 0.75
        assert data["message"] == "Render parameters updated."

    @pytest.mark.asyncio
    async def test_adjust_style_template(self):
        """Test adjusting style_template parameter."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/render/adjust", json={"style_template": "Literary"})

        assert response.status_code == 200
        data = response.json()
        assert data["default_render_mixer"]["style_template"] == "Literary"

    @pytest.mark.asyncio
    async def test_adjust_pov_type(self):
        """Test adjusting pov_type parameter."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/render/adjust", json={"pov_type": "FIRST_PERSON"})

        assert response.status_code == 200
        data = response.json()
        assert data["default_render_mixer"]["pov_type"] == "FIRST_PERSON"

    @pytest.mark.asyncio
    async def test_adjust_multiple_parameters(self):
        """Test adjusting multiple parameters at once."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/render/adjust",
                json={
                    "subtext_ratio": 0.9,
                    "style_template": "Poetic",
                    "pov_type": "CHARACTER_LIMITED",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["default_render_mixer"]["subtext_ratio"] == 0.9
        assert data["default_render_mixer"]["style_template"] == "Poetic"
        assert data["default_render_mixer"]["pov_type"] == "CHARACTER_LIMITED"

    @pytest.mark.asyncio
    async def test_adjust_empty_request_keeps_defaults(self):
        """Test that empty request keeps current settings."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # First, set some values
            await ac.post("/api/v1/render/adjust", json={"subtext_ratio": 0.8})

            # Empty request should keep current values
            response = await ac.post("/api/v1/render/adjust", json={})

        assert response.status_code == 200
        data = response.json()
        # Should still have the previously set value
        assert data["default_render_mixer"]["subtext_ratio"] == 0.8

    @pytest.mark.asyncio
    async def test_adjust_subtext_ratio_validation_below_zero(self):
        """Test that subtext_ratio below 0 is rejected."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/render/adjust", json={"subtext_ratio": -0.1})

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_adjust_subtext_ratio_validation_above_one(self):
        """Test that subtext_ratio above 1 is rejected."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/render/adjust", json={"subtext_ratio": 1.5})

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_adjust_persists_to_database(self):
        """Test that adjustments persist to database."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Adjust parameters
            await ac.post(
                "/api/v1/render/adjust",
                json={"subtext_ratio": 0.33, "style_template": "Minimalist"},
            )

            # Fetch settings to verify persistence
            settings_response = await ac.get("/api/v1/settings")

        assert settings_response.status_code == 200
        settings = settings_response.json()
        assert settings["settings"]["default_render_mixer"]["subtext_ratio"] == 0.33
        assert settings["settings"]["default_render_mixer"]["style_template"] == "Minimalist"
