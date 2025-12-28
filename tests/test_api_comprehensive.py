import pytest
from httpx import AsyncClient
from app.main import app

API_KEY = "kasparro_secret_key_2025"

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health endpoint returns correct structure"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    
    assert response.status_code in [200, 500]
    data = response.json()
    assert "status" in data

@pytest.mark.asyncio
async def test_data_endpoint_requires_auth():
    """Test data endpoint requires API key"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/data")
    
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data

@pytest.mark.asyncio
async def test_data_endpoint_with_invalid_key():
    """Test data endpoint rejects invalid API key"""
    headers = {"X-API-Key": "wrong-key"}
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/data", headers=headers)
    
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_stats_endpoint_requires_auth():
    """Test stats endpoint requires API key"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/stats")
    
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_invalid_pagination():
    """Test API handles invalid pagination"""
    headers = {"X-API-Key": API_KEY}
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/data?page=0", headers=headers)
    
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_etl_endpoint_requires_auth():
    """Test ETL trigger endpoint requires API key"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/etl/run")
    
    assert response.status_code == 403
