import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.main import app
from app.db.session import engine
from app.models.user import User
from app.models.project import Project
from app.models.chapter import Chapter, Block, VariantType
from app.core import security
from uuid import uuid4

client = TestClient(app)

@pytest.fixture
def auth_headers():
    with Session(engine) as session:
        email = f"blocktest_{uuid4()}@example.com"
        user = User(email=email, hashed_password=security.get_password_hash("password"))
        session.add(user)
        session.commit()
        session.refresh(user)
        
        project = Project(title="Block Project", owner_id=user.id)
        session.add(project)
        session.commit()
        session.refresh(project)
        
        chapter = Chapter(title="Chapter 1", project_id=project.id)
        session.add(chapter)
        session.commit()
        session.refresh(chapter)
        
        # Create a block with an AI variant
        block = Block(
            chapter_id=chapter.id,
            variants=[{
                "id": str(uuid4()),
                "type": "ai",
                "label": "Original",
                "text": "Hello world",
                "style_tag": "test"
            }],
            selected_variant_index=0,
            content_snapshot="Hello world"
        )
        session.add(block)
        session.commit()
        session.refresh(block)
        
        token = security.create_access_token(user.id)
        return {
            "Authorization": f"Bearer {token}",
            "block_id": block.id,
            "user_id": user.id
        }

def test_block_consistency_error(auth_headers):
    # Missing content_snapshot when updating index
    response = client.patch(
        f"/api/v1/blocks/{auth_headers['block_id']}",
        headers={"Authorization": auth_headers["Authorization"]},
        json={"selected_variant_index": 0}
    )
    # Pydantic validator should catch this
    assert response.status_code == 422

def test_block_fork_scenario_b(auth_headers):
    # Edit AI variant -> Should create USER_CUSTOM variant
    new_text = "Edited by user"
    response = client.patch(
        f"/api/v1/blocks/{auth_headers['block_id']}",
        headers={"Authorization": auth_headers["Authorization"]},
        json={
            "selected_variant_index": 0,
            "content_snapshot": new_text
        }
    )
    assert response.status_code == 200
    data = response.json()
    
    # Assertions
    assert len(data["variants"]) == 2
    assert data["selected_variant_index"] == 1
    assert data["variants"][1]["type"] == "user"
    assert data["variants"][1]["text"] == new_text
    assert data["content_snapshot"] == new_text

def test_block_in_place_update_scenario_c(auth_headers):
    # First, create a user custom variant
    client.patch(
        f"/api/v1/blocks/{auth_headers['block_id']}",
        headers={"Authorization": auth_headers["Authorization"]},
        json={"selected_variant_index": 0, "content_snapshot": "First edit"}
    )
    
    # Now edit it again
    response = client.patch(
        f"/api/v1/blocks/{auth_headers['block_id']}",
        headers={"Authorization": auth_headers["Authorization"]},
        json={"selected_variant_index": 1, "content_snapshot": "Second edit"}
    )
    
    data = response.json()
    # Should still have only 2 variants (Scenario C: In-Place)
    assert len(data["variants"]) == 2
    assert data["selected_variant_index"] == 1
    assert data["variants"][1]["text"] == "Second edit"
