import pytest
from fastapi.testclient import TestClient
from main import app 

client = TestClient(app)

def test_get_root_endpoint():
    """Test api root"""
    response = client.get("/")
    assert response.status_code == 200

def test_get_healt_endpoint():
    """Test api root"""
    response = client.get("/health")
    assert response.status_code == 200
    status = response.json()["status"]
    timestamp = response.json()["timestamp"]
    assert status == "healthy"
    assert timestamp
    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
