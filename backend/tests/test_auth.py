import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from app.main import app
from app.db.session import engine

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    SQLModel.metadata.create_all(engine)
    yield
    # Optional: cleanup after tests if needed
    # SQLModel.metadata.drop_all(engine)

def test_register():
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

def test_login():
    # Login with the registered user
    response = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_incorrect_password():
    response = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "test@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect email or password"
