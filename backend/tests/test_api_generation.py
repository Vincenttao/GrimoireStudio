import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from uuid import uuid4
from app.main import app
from app.db.session import engine
from app.models.user import User
from app.models.project import Project
from app.models.chapter import Chapter, NarrativeMode
from app.core import security

client = TestClient(app)

@pytest.fixture
def auth_headers():
    with Session(engine) as session:
        email = "gentest@example.com"
        user = session.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, hashed_password=security.get_password_hash("password"))
            session.add(user)
            session.commit()
            session.refresh(user)
        
        token = security.create_access_token(user.id)
        return {"Authorization": f"Bearer {token}", "user_id": user.id}

def test_generate_beat_idor(auth_headers):
    # Create a project and chapter for another user
    with Session(engine) as session:
        user_b_email = f"other_{uuid4()}@example.com"
        user_b = User(email=user_b_email, hashed_password="pw")
        session.add(user_b)
        session.commit()
        session.refresh(user_b)
        
        project_b = Project(title="Other Project", owner_id=user_b.id)
        session.add(project_b)
        session.commit()
        session.refresh(project_b)
        
        chapter_b = Chapter(title="Other Chapter", project_id=project_b.id)
        session.add(chapter_b)
        session.commit()
        session.refresh(chapter_b)
        
        other_chapter_id = chapter_b.id

    # User A tries to generate in User B's chapter
    response = client.post(
        "/api/v1/generation/beat",
        headers={"Authorization": auth_headers["Authorization"]},
        json={
            "project_id": 999,
            "chapter_id": other_chapter_id,
            "narrative_mode": "standard"
        }
    )
    assert response.status_code == 404

def test_generate_beat_success(auth_headers):
    with Session(engine) as session:
        project = Project(title=f"My Project {uuid4()}", owner_id=auth_headers["user_id"])
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id
        
        chapter = Chapter(title="My Chapter", project_id=project_id)
        session.add(chapter)
        session.commit()
        session.refresh(chapter)
        chapter_id = chapter.id

    response = client.post(
        "/api/v1/generation/beat",
        headers={"Authorization": auth_headers["Authorization"]},
        json={
            "project_id": project_id,
            "chapter_id": chapter_id,
            "narrative_mode": "sensory_lens",
            "preceding_context": "The wind was cold."
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "generated_rank" in data
    assert len(data["variants"]) == 3
    assert data["variants"][0]["type"] == "ai"
    assert "scrying_glass" in data["meta_info"]
