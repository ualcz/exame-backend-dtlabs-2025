import pytest
import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.main import app, Base
from app.database import get_db
from app.security.auth import get_password_hash 
from app.models.models import DBUser, DBServer

# Test database
SQLALCHEMY_DATABASE_URL = "postgresql://neondb_owner:npg_hOBaysAmu63w@ep-green-dawn-a5qt2yg1-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Fixture to create/drop test database before/after tests
@pytest.fixture(scope="function")
def test_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Add test data
    db = TestingSessionLocal()
    test_user = DBUser(
        id="01HQNJ3P8TMRZ5QPBHF3GPTVWH",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword"),
        disabled=False
    )
    
    test_server = DBServer(
        server_ulid="01HQNJ4RT8Z6MSPMTC83WTPQTA",
        server_name="Test Server",
        owner_id="01HQNJ3P8TMRZ5QPBHF3GPTVWH",
        last_seen=datetime.now()
    )
    
    offline_server = DBServer(
        server_ulid="01HQNJ5WF7Q24KPJDVA0SXMHBR",
        server_name="Offline Server",
        owner_id="01HQNJ3P8TMRZ5QPBHF3GPTVWH",
        last_seen=datetime.now() - timedelta(seconds=15)
    )
    
    db.add(test_user)
    db.add(test_server)
    db.add(offline_server)
    db.commit()
    
    # Override dependency
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield
    
    # Clean up
    db.close()
    Base.metadata.drop_all(bind=engine)


# Client for making test requests
@pytest.fixture(scope="function")
def client(test_db):
    with TestClient(app) as c:
        yield c


# Helper function to get auth token
def get_auth_token(client):
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpassword"}
    )
    return response.json()["access_token"]


# Test user registration
def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "full_name": "New User",
            "password": "newpassword"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert data["full_name"] == "New User"


# Test user login
def test_login(client):
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# Test create server
def test_create_server(client):
    token = get_auth_token(client)
    response = client.post(
        "/servers",
        json={"server_name": "New Server"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["server_name"] == "New Server"
    assert "server_ulid" in data
    assert data["status"] == "online"


# Test post sensor data
def test_post_sensor_data(client):
    response = client.post(
        "/data",
        json={
            "server_ulid": "01HQNJ4RT8Z6MSPMTC83WTPQTA",
            "timestamp": datetime.now().isoformat(),
            "temperature": 25.5,
            "humidity": 60.0
        }
    )
    assert response.status_code == 201
    assert response.json()["message"] == "Data recorded successfully"


# Test post sensor data - server not found
def test_post_sensor_data_server_not_found(client):
    response = client.post(
        "/data",
        json={
            "server_ulid": "NONEXISTENT",
            "timestamp": datetime.now().isoformat(),
            "temperature": 25.5
        }
    )
    assert response.status_code == 404
    assert "Server not found" in response.json()["detail"]


# Test post sensor data - no sensor values
def test_post_sensor_data_no_sensors(client):
    response = client.post(
        "/data",
        json={
            "server_ulid": "01HQNJ4RT8Z6MSPMTC83WTPQTA",
            "timestamp": datetime.now().isoformat()
        }
    )
    assert response.status_code == 422


# Test get sensor data
def test_get_sensor_data(client):
    # First post some data
    client.post(
        "/data",
        json={
            "server_ulid": "01HQNJ4RT8Z6MSPMTC83WTPQTA",
            "timestamp": datetime.now().isoformat(),
            "temperature": 25.5,
            "humidity": 60.0
        }
    )
    
    # Get the data
    token = get_auth_token(client)
    response = client.get(
        "/data",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "timestamp" in data[0]
    assert "temperature" in data[0]


# Test all servers health endpoint
def test_all_servers_health(client):
    token = get_auth_token(client)
    response = client.get(
        "/health/all", 
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    
    # Check that we have both online and offline servers
    statuses = [server["status"] for server in data]
    assert "online" in statuses
    assert "offline" in statuses
    
def test_server_health(client):
    token = get_auth_token(client)
    
    # Test online server
    response = client.post(
        "/servers",
        json={"server_name": "Test Server"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    server_ulid = response.json()["server_ulid"]
    
    # Verificando o status do servidor logo após a criação
    response = client.get(
        f"/health/{server_ulid}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    
    time.sleep(10)
    
    # Test offline server (simulate offline by changing last_seen in the DB or waiting)
    response = client.get(
        "/health/01HQNJ5WF7Q24KPJDVA0SXMHBR",  # Use a known offline server id
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "offline"
