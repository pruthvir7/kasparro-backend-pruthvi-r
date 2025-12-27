import pytest

@pytest.mark.asyncio
async def test_etl_imports():
    """Test ETL modules can be imported"""
    from app.etl.coinpaprika_etl import CoinPaprikaETL
    from app.etl.coingecko_etl import CoinGeckoETL
    from app.etl.csv_etl import CSVETL
    
    assert CoinPaprikaETL is not None
    assert CoinGeckoETL is not None
    assert CSVETL is not None

@pytest.mark.asyncio
async def test_models_import():
    """Test models can be imported"""
    from app.models.models import CryptoCurrency, Checkpoint, ETLRun
    
    assert CryptoCurrency is not None
    assert Checkpoint is not None
    assert ETLRun is not None
