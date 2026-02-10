import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.main import app
from app.db.session import engine
from app.models.user import User
from app.models.project import Project
from app.core import security
from uuid import uuid4

client = TestClient(app)

@pytest.fixture
def auth_data():
    with Session(engine) as session:
        email = f"smoothtest_{uuid4()}@example.com"
        user = User(email=email, hashed_password=security.get_password_hash("password"))
        session.add(user)
        session.commit()
        session.refresh(user)
        
        project = Project(title="Smoothing Project", owner_id=user.id)
        session.add(project)
        session.commit()
        session.refresh(project)
        
        token = security.create_access_token(user.id)
        return {
            "headers": {"Authorization": f"Bearer {token}"},
            "project_id": project.id
        }

def test_smooth_transition_success(auth_data):
    key = str(uuid4())
    response = client.post(
        "/api/v1/generation/smooth",
        headers=auth_data["headers"],
        json={
            "prev_block_text": "Alice slapped Bob.",
            "next_block_text": "Bob smiled warmly.",
            "idempotency_key": key,
            "project_id": auth_data["project_id"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["needs_smoothing"] is True
    assert "Smoothed transition" in data["smoothed_text"]

def test_smooth_transition_idempotency(auth_data):
    key = "same-key"
    payload = {
        "prev_block_text": "A",
        "next_block_text": "B",
        "idempotency_key": key,
        "project_id": auth_data["project_id"]
    }
    # First call
    res1 = client.post("/api/v1/generation/smooth", headers=auth_data["headers"], json=payload)
    # Second call
    res2 = client.post("/api/v1/generation/smooth", headers=auth_data["headers"], json=payload)
    
    assert res1.json() == res2.json()

def test_smooth_transition_empty_next(auth_data):
    response = client.post(
        "/api/v1/generation/smooth",
        headers=auth_data["headers"],
        json={
            "prev_block_text": "End of story.",
            "next_block_text": "",
            "idempotency_key": "empty-test",
            "project_id": auth_data["project_id"]
        }
    )
    assert response.status_code == 200
    assert response.json()["needs_smoothing"] is False
