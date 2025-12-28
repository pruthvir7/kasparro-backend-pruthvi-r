import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.models import Base
import os

# Use test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def async_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture(scope="function")
async def async_session(async_engine):
    """Create test database session"""
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session

@pytest.fixture
def sample_crypto_data():
    """Sample cryptocurrency data for testing"""
    return [
        {
            "coin_id": "btc-bitcoin",
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 50000.0,
            "market_cap": 1000000000000.0,
            "volume_24h": 50000000000.0,
            "source": "test",
            "last_updated": "2025-12-28T00:00:00"
        }
    ]
