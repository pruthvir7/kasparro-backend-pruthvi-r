from fastapi import APIRouter, Depends, Query, HTTPException
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
import structlog
from typing import Optional
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY
from fastapi.responses import Response
from app.utils.metrics import (
    api_requests_total,
    api_request_duration,
    crypto_records_total
)
from app.core.auth import verify_api_key

logger = structlog.get_logger()

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


@router.get("/data")  # ✅ Fixed: @router instead of @app
async def get_data(
    coin: Optional[str] = None,
    source: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Get cryptocurrency price data (normalized).
    
    Returns price records with canonical coin references.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        # Build query joining normalized tables
        query = select(
            CoinPrice.id,
            Coin.id.label("coin_id"),
            Coin.symbol,
            Coin.name,
            CoinPrice.price_usd,
            CoinPrice.market_cap,
            CoinPrice.volume_24h,
            CoinPrice.source,
            CoinPrice.timestamp.label("last_updated")
        ).join(
            Coin, CoinPrice.coin_id == Coin.id
        )
        
        # Apply filters
        if coin:
            query = query.filter(Coin.symbol == coin.upper())
        if source:
            query = query.filter(CoinPrice.source == source)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()
        
        # Apply pagination
        query = query.order_by(CoinPrice.timestamp.desc())
        query = query.offset((page - 1) * limit).limit(limit)
        
        # Execute
        result = await db.execute(query)
        rows = result.fetchall()
        
        # Format response
        data = [
            {
                "id": row.id,
                "coin_id": row.coin_id,
                "symbol": row.symbol,
                "name": row.name,
                "price_usd": float(row.price_usd) if row.price_usd else None,
                "market_cap": float(row.market_cap) if row.market_cap else None,
                "volume_24h": float(row.volume_24h) if row.volume_24h else None,
                "source": row.source,
                "last_updated": row.last_updated.isoformat() if row.last_updated else None
            }
            for row in rows
        ]
        
        latency_ms = round((time.time() - start_time) * 1000, 2)
        
        return {
            "request_id": request_id,
            "api_latency_ms": latency_ms,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "data": data
        }
        
    except Exception as e:
        logger.error(f"Error in get_data: {e}", request_id=request_id)
        raise HTTPException(status_code=500, detail=str(e))


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
    limit: int = Query(20, ge=1, le=100),  # ✅ Added pagination
    page: int = Query(1, ge=1),
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
            .offset((page - 1) * limit)
            .limit(limit)
        )
        
        # Group by coin
        coins_dict = {}
        for coin, identifier in result.all():
            if coin.id not in coins_dict:  # ✅ Use coin.id instead of symbol (handles duplicates better)
                coins_dict[coin.id] = {
                    "id": coin.id,
                    "symbol": coin.symbol,
                    "name": coin.name,
                    "created_at": coin.created_at.isoformat(),
                    "source_identifiers": []
                }
            
            coins_dict[coin.id]["source_identifiers"].append({
                "source": identifier.source,
                "source_id": identifier.source_id,
                "created_at": identifier.created_at.isoformat()
            })
        
        # Get total count
        count_result = await db.execute(select(func.count(distinct(Coin.id))))
        total_count = count_result.scalar()
        
        return {
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "coins": list(coins_dict.values())
        }
        
    except Exception as e:
        logger.error(f"Error in get_canonical_coins: {e}")
        raise HTTPException(status_code=500, detail=str(e))
