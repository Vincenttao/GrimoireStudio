import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.db.session import engine
from app.models.user import User
from app.models.project import Project
from app.models.entity import Entity, EntityAlias
from app.core import security
from uuid import uuid4

client = TestClient(app)

@pytest.fixture
def auth_data():
    with Session(engine) as session:
        email = f"entitytest_{uuid4()}@example.com"
        user = User(email=email, hashed_password=security.get_password_hash("password"))
        session.add(user)
        session.commit()
        session.refresh(user)
        
        project = Project(title="Test Project", owner_id=user.id)
        session.add(project)
        session.commit()
        session.refresh(project)
        
        token = security.create_access_token(user.id)
        return {
            "token": token,
            "user_id": user.id,
            "project_id": project.id,
            "headers": {"Authorization": f"Bearer {token}"}
        }

def test_create_entity_with_aliases(auth_data):
    response = client.post(
        "/api/v1/entities/",
        headers=auth_data["headers"],
        json={
            "project_id": auth_data["project_id"],
            "name": "Batman",
            "type": "character",
            "description": "Dark Knight",
            "aliases": ["Bruce", "Bats"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Batman"
    assert set(data["aliases"]) == {"Bruce", "Bats"}

def test_update_entity_alias_set_arithmetic(auth_data):
    # 1. Create initial entity
    res = client.post(
        "/api/v1/entities/",
        headers=auth_data["headers"],
        json={
            "project_id": auth_data["project_id"],
            "name": "Superman",
            "type": "character",
            "description": "Man of Steel",
            "aliases": ["Clark", "Kal-El"]
        }
    )
    entity_id = res.json()["id"]

    # 2. Update aliases: remove 'Clark', keep 'Kal-El', add 'Smallville'
    res_update = client.put(
        f"/api/v1/entities/{entity_id}",
        headers=auth_data["headers"],
        json={"aliases": ["Kal-El", "Smallville"]}
    )
    assert res_update.status_code == 200
    data = res_update.json()
    assert set(data["aliases"]) == {"Kal-El", "Smallville"}
    
    # 3. Verify in DB
    with Session(engine) as session:
        aliases = session.exec(select(EntityAlias).where(EntityAlias.entity_id == entity_id)).all()
        alias_names = {a.alias for a in aliases}
        assert alias_names == {"Kal-El", "Smallville"}

def test_entity_idor_masking(auth_data):
    # User B creates an entity
    with Session(engine) as session:
        user_b = User(email=f"userb_{uuid4()}@example.com", hashed_password="pw")
        session.add(user_b)
        session.commit()
        project_b = Project(title="B Project", owner_id=user_b.id)
        session.add(project_b)
        session.commit()
        entity_b = Entity(project_id=project_b.id, name="Secret", type="character", description="...")
        session.add(entity_b)
        session.commit()
        session.refresh(entity_b)
        secret_id = entity_b.id

    # User A tries to access User B's entity
    response = client.get(f"/api/v1/entities/{secret_id}", headers=auth_data["headers"])
    assert response.status_code == 404
