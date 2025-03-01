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
import uuid

# Test database
SQLALCHEMY_DATABASE_URL = "postgresql://clau:c123456@localhost:5432/dtlabs?sslmode=disable"

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


# Test authentication failure
def test_authentication_required(client):
    response = client.get("/data")  # Tentativa sem token
    assert response.status_code == 401

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


def test_invalid_timestamp_format(client):
    response = client.post(
        "/data",
        json={
            "server_ulid": "01HQNJ4RT8Z6MSPMTC83WTPQTA",
            "timestamp": "invalid-timestamp",
            "temperature": 22.5
        }
    )
    assert response.status_code == 422


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


# Test GET /data with server_ulid filter
def test_get_sensor_data_by_server(client):
    token = get_auth_token(client)
    
    # First post some test data for different servers
    server_id = "01HQNJ4RT8Z6MSPMTC83WTPQTA"
    
    # Post data for the first server
    client.post(
        "/data",
        json={
            "server_ulid": server_id,
            "timestamp": datetime.now().isoformat(),
            "temperature": 25.5,
            "humidity": 60.0
        }
    )
    
    # Get the data filtered by server_ulid
    response = client.get(
        f"/data?server_ulid={server_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0



# Test GET /data with time range filter
def test_get_sensor_data_by_time_range(client):
    token = get_auth_token(client)
    
    # Create timestamps for our test
    now = datetime.now()
    start_time = (now - timedelta(hours=1)).isoformat()
    mid_time = now.isoformat()
    end_time = (now + timedelta(hours=1)).isoformat()
    
    # Post data with timestamp in the middle of our range
    client.post(
        "/data",
        json={
            "server_ulid": "01HQNJ4RT8Z6MSPMTC83WTPQTA",
            "timestamp": mid_time,
            "temperature": 25.5
        }
    )
    
    # Get data within time range
    response = client.get(
        f"/data?start_time={start_time}&end_time={end_time}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# Test GET /data with sensor_type filter
def test_get_sensor_data_by_sensor_type(client):
    token = get_auth_token(client)
    
    # Post data with multiple sensor types
    client.post(
        "/data",
        json={
            "server_ulid": "01HQNJ4RT8Z6MSPMTC83WTPQTA",
            "timestamp": datetime.now().isoformat(),
            "temperature": 25.5,
            "humidity": 60.0,
            "voltage": 220.0,
            "current": 1.5
        }
    )
    
    # Test each sensor type individually
    sensor_types = ["temperature", "humidity", "voltage", "current"]
    
    for sensor in sensor_types:
        response = client.get(
            f"/data?sensor_type={sensor}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# Test combining multiple filters
def test_get_sensor_data_with_combined_filters(client):
    token = get_auth_token(client)
    
    # Use a specific server and time range
    server_id = "01HQNJ4RT8Z6MSPMTC83WTPQTA"
    now = datetime.now()
    start_time = (now - timedelta(hours=1)).isoformat()
    end_time = (now + timedelta(hours=1)).isoformat()
    
    # Post test data
    client.post(
        "/data",
        json={
            "server_ulid": server_id,
            "timestamp": now.isoformat(),
            "temperature": 25.5,
            "humidity": 60.0
        }
    )
    
    # Get data with combined filters
    response = client.get(
        f"/data?server_ulid={server_id}&start_time={start_time}&end_time={end_time}&sensor_type=temperature",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# Test invalid parameters
def test_get_sensor_data_with_invalid_parameters(client):
    token = get_auth_token(client)
    
    # Test invalid aggregation parameter
    response = client.get(
        "/data?aggregation=invalid",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code in [400, 422]
    
    # Test invalid date format
    response = client.get(
        "/data?start_time=invalid-date",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code in [400, 422]
    
    # Test invalid sensor type
    response = client.get(
        "/data?sensor_type=invalid_sensor",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code in [400, 422]


# Additional test for server registration with unique name
def test_create_server_with_unique_name(client):
    token = get_auth_token(client)
    
    unique_name = f"Server {uuid.uuid4()}"
    
    response = client.post(
        "/servers",
        json={"server_name": unique_name},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["server_name"] == unique_name
