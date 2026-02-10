import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.db.session import engine
from app.models.user import User
from app.models.project import Project
from app.core import security

client = TestClient(app)

@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session

def test_tenancy_isolation(db_session: Session):
    # 1. Create User A and User B
    user_a_email = "usera@example.com"
    user_b_email = "userb@example.com"
    
    for email in [user_a_email, user_b_email]:
        existing = db_session.exec(select(User).where(User.email == email)).first()
        if existing:
            db_session.delete(existing)
    db_session.commit()

    user_a = User(email=user_a_email, hashed_password=security.get_password_hash("password"))
    user_b = User(email=user_b_email, hashed_password=security.get_password_hash("password"))
    db_session.add(user_a)
    db_session.add(user_b)
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    # 2. User B creates a project
    project_b = Project(title="User B Project", owner_id=user_b.id)
    db_session.add(project_b)
    db_session.commit()
    db_session.refresh(project_b)

    # 3. User A logs in
    response_login = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": user_a_email, "password": "password"},
    )
    token_a = response_login.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 4. User A tries to access User B's project
    response = client.get(f"/api/v1/projects/{project_b.id}", headers=headers_a)
    
    # Standard: Must return 404 Not Found (not 403)
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"

    # 5. User A tries to update User B's project
    response = client.put(
        f"/api/v1/projects/{project_b.id}", 
        headers=headers_a,
        json={"title": "Hacked"}
    )
    assert response.status_code == 404

    # 6. User A tries to delete User B's project
    response = client.delete(f"/api/v1/projects/{project_b.id}", headers=headers_a)
    assert response.status_code == 404
