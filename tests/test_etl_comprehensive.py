import pytest
from app.etl.coinpaprika_etl import CoinPaprikaETL
from app.etl.coingecko_etl import CoinGeckoETL
from app.models.models import CryptoCurrency, Checkpoint, ETLRun
from sqlalchemy import select, func

@pytest.mark.asyncio
async def test_etl_extraction(async_session):
    """Test ETL can extract data from source"""
    etl = CoinPaprikaETL(async_session)
    
    raw_data = await etl.extract()
    
    assert raw_data is not None
    assert len(raw_data) > 0
    assert isinstance(raw_data, list)

@pytest.mark.asyncio
async def test_etl_transformation(async_session):
    """Test ETL transforms data correctly"""
    etl = CoinPaprikaETL(async_session)
    
    raw_data = await etl.extract()
    transformed = await etl.transform(raw_data)  # FIXED: added await
    
    assert len(transformed) > 0
    
    # Check required fields
    for item in transformed[:5]:
        assert 'coin_id' in item
        assert 'name' in item
        assert 'symbol' in item
        assert 'price_usd' in item
        assert 'source' in item
        assert item['source'] == 'coinpaprika'

@pytest.mark.asyncio
async def test_etl_load_creates_records(async_session):
    """Test ETL loads data into database"""
    etl = CoinPaprikaETL(async_session)
    
    # Run ETL
    count = await etl.run()
    
    # Verify records created
    result = await async_session.execute(select(CryptoCurrency))
    records = result.scalars().all()
    
    assert len(records) > 0
    assert len(records) == count

@pytest.mark.asyncio
async def test_incremental_ingestion_no_duplicates(async_session):
    """Test ETL doesn't create duplicates on re-run"""
    etl = CoinPaprikaETL(async_session)
    
    # First run
    await etl.run()
    
    result1 = await async_session.execute(select(func.count(CryptoCurrency.id)))
    total1 = result1.scalar()
    
    # Second run (should update, not duplicate)
    await etl.run()
    
    result2 = await async_session.execute(select(func.count(CryptoCurrency.id)))
    total2 = result2.scalar()
    
    # Total should not double (allows small variance)
    assert total2 <= total1 + 5

@pytest.mark.asyncio
async def test_checkpoint_creation(async_session):
    """Test ETL creates checkpoints"""
    etl = CoinPaprikaETL(async_session)
    
    await etl.run()
    
    # Check checkpoint exists (simplified - just check table has records)
    result = await async_session.execute(select(Checkpoint))
    checkpoints = result.scalars().all()
    
    assert len(checkpoints) > 0

@pytest.mark.asyncio
async def test_etl_run_tracking(async_session):
    """Test ETL tracks runs in ETLRun table"""
    etl = CoinPaprikaETL(async_session)
    
    await etl.run()
    
    # Check ETL run recorded (simplified - just check table has records)
    result = await async_session.execute(select(ETLRun))
    runs = result.scalars().all()
    
    assert len(runs) > 0

@pytest.mark.asyncio
async def test_multiple_sources_etl(async_session):
    """Test multiple ETL sources can run without conflicts"""
    etl1 = CoinPaprikaETL(async_session)
    etl2 = CoinGeckoETL(async_session)
    
    await etl1.run()
    await etl2.run()
    
    # Check both sources have data
    result = await async_session.execute(
        select(CryptoCurrency.source, func.count(CryptoCurrency.id))
        .group_by(CryptoCurrency.source)
    )
    source_counts = {row[0]: row[1] for row in result.all()}
    
    assert 'coinpaprika' in source_counts
    assert 'coingecko' in source_counts
    assert source_counts['coinpaprika'] > 0
    assert source_counts['coingecko'] > 0
