from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, distinct
from app.core.database import get_db
from app.models.models import (
    CryptoCurrency, Checkpoint, ETLRun,
    Coin, CoinPrice, CoinIdentifier  # NEW: Normalized models
)
from app.schemas.crypto import DataResponse, CryptoResponse, HealthResponse, StatsResponse
import uuid
import time
from typing import Optional
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY
from fastapi.responses import Response
from app.utils.metrics import (
    api_requests_total,
    api_request_duration,
    crypto_records_total
)
from app.core.auth import verify_api_key


router = APIRouter()


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint - No auth required for monitoring"""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check system health - No auth for health checks"""
    try:
        # Test DB connection
        await db.execute(select(1))
        db_status = "connected"
        
        # Get last ETL run
        result = await db.execute(
            select(ETLRun).order_by(desc(ETLRun.start_time)).limit(1)
        )
        last_run = result.scalar_one_or_none()
        
        return HealthResponse(
            status="healthy",
            database=db_status,
            etl_last_run=last_run.start_time if last_run else None,
            etl_status=last_run.status if last_run else None
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            database=f"error: {str(e)}",
            etl_last_run=None,
            etl_status=None
        )


@router.get("/data", response_model=DataResponse)
async def get_data(
    coin: Optional[str] = None,
    source: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get cryptocurrency data from NORMALIZED SCHEMA.
    
    NEW: Returns data where coins are unified across sources.
    BTC from CoinPaprika + BTC from CoinGecko = ONE Bitcoin entity.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Build query for normalized data (Coin + CoinPrice)
    query = (
        select(
            Coin.id,
            Coin.symbol,
            Coin.name,
            CoinPrice.price_usd,
            CoinPrice.market_cap,
            CoinPrice.volume_24h,
            CoinPrice.source,
            CoinPrice.timestamp
        )
        .join(CoinPrice, Coin.id == CoinPrice.coin_id)
        .order_by(Coin.symbol, CoinPrice.timestamp.desc())
    )
    
    # Apply filters
    if coin:
        query = query.where(Coin.symbol == coin.upper())
    if source:
        query = query.where(CoinPrice.source == source)
    
    # Get total count (unique coins, not price records)
    count_query = select(func.count(distinct(Coin.id))).select_from(Coin).join(CoinPrice)
    if coin:
        count_query = count_query.where(Coin.symbol == coin.upper())
    if source:
        count_query = count_query.where(CoinPrice.source == source)
    
    total_result = await db.execute(count_query)
    total_count = total_result.scalar()
    
    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    records = result.all()
    
    # Format data
    data = []
    for record in records:
        data.append({
            "id": record.id,
            "coin_id": f"{record.source}:{record.symbol}",  # Keep for compatibility
            "name": record.name,
            "symbol": record.symbol,
            "price_usd": record.price_usd,
            "market_cap": record.market_cap,
            "volume_24h": record.volume_24h,
            "source": record.source,
            "last_updated": record.timestamp
        })
    
    latency = (time.time() - start_time) * 1000
    
    return DataResponse(
        request_id=request_id,
        api_latency_ms=round(latency, 2),
        total_count=total_count,
        page=page,
        limit=limit,
        data=data
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get ETL statistics from NORMALIZED SCHEMA.
    
    NEW: Shows stats based on canonical coins (unified across sources).
    """
    # Total canonical coins (unique entities)
    coin_count_result = await db.execute(select(func.count(Coin.id)))
    total_coins = coin_count_result.scalar()
    
    # Total price records
    price_count_result = await db.execute(select(func.count(CoinPrice.id)))
    total_records = price_count_result.scalar()
    
    # Records by source
    source_result = await db.execute(
        select(CoinPrice.source, func.count(CoinPrice.id))
        .group_by(CoinPrice.source)
    )
    records_by_source = {row[0]: row[1] for row in source_result.all()}
    
    # Last success
    success_result = await db.execute(
        select(ETLRun.end_time)
        .where(ETLRun.status == "success")
        .order_by(desc(ETLRun.end_time))
        .limit(1)
    )
    last_success = success_result.scalar_one_or_none()
    
    # Last failure
    failure_result = await db.execute(
        select(ETLRun.end_time)
        .where(ETLRun.status == "failed")
        .order_by(desc(ETLRun.end_time))
        .limit(1)
    )
    last_failure = failure_result.scalar_one_or_none()
    
    # Average duration
    avg_result = await db.execute(
        select(func.avg(ETLRun.duration_seconds))
        .where(ETLRun.status == "success")
    )
    avg_duration = avg_result.scalar()
    
    # Count unique sources
    source_count_result = await db.execute(
        select(func.count(distinct(CoinPrice.source)))
    )
    total_sources = source_count_result.scalar()
    
    return StatsResponse(
        total_records=total_records,
        total_sources=total_sources,
        last_success=last_success,
        last_failure=last_failure,
        avg_duration_seconds=round(avg_duration, 2) if avg_duration else None,
        records_by_source=records_by_source
    )


@router.post("/etl/run")
async def trigger_etl(
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Manually trigger all ETL pipelines.
    
    NEW: ETL now loads data into normalized schema (Coin -> CoinPrice).
    """
    try:
        from app.etl.coinpaprika_etl import CoinPaprikaETL
        from app.etl.coingecko_etl import CoinGeckoETL
        from app.etl.csv_etl import CSVETL
        
        etls = [
            CoinPaprikaETL(db),
            CoinGeckoETL(db),
            CSVETL(db, "/app/data/sample_crypto.csv")
        ]
        
        results = []
        for etl in etls:
            try:
                count = await etl.run()
                results.append({
                    "source": etl.source_name,
                    "records": count,
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "source": etl.source_name,
                    "records": 0,
                    "status": "failed",
                    "error": str(e)
                })
        
        return {
            "status": "success",
            "message": "ETL pipelines completed",
            "results": results
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/coins")
async def get_canonical_coins(
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    NEW ENDPOINT: Get list of canonical coins with source mappings.
    
    Shows how coins are unified across sources.
    Example: BTC has identifiers from coinpaprika (btc-bitcoin), coingecko (bitcoin), csv (btc)
    """
    try:
        # Get all coins with their identifiers
        result = await db.execute(
            select(Coin, CoinIdentifier)
            .join(CoinIdentifier, Coin.id == CoinIdentifier.coin_id)
            .order_by(Coin.symbol)
        )
        
        # Group by coin
        coins_dict = {}
        for coin, identifier in result.all():
            if coin.symbol not in coins_dict:
                coins_dict[coin.symbol] = {
                    "symbol": coin.symbol,
                    "name": coin.name,
                    "created_at": coin.created_at.isoformat(),
                    "source_identifiers": []
                }
            
            coins_dict[coin.symbol]["source_identifiers"].append({
                "source": identifier.source,
                "source_id": identifier.source_id
            })
        
        return {
            "total_coins": len(coins_dict),
            "coins": list(coins_dict.values())
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
