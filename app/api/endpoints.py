from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.core.database import get_db
from app.models.models import CryptoCurrency, Checkpoint, ETLRun
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
import time


router = APIRouter()

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check system health"""
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
    db: AsyncSession = Depends(get_db)
):
    """Get cryptocurrency data with filters and pagination"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Build query
    query = select(CryptoCurrency)
    if coin:
        query = query.where(CryptoCurrency.symbol == coin.upper())
    if source:
        query = query.where(CryptoCurrency.source == source)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar()
    
    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    data = result.scalars().all()
    
    latency = (time.time() - start_time) * 1000
    
    return DataResponse(
        request_id=request_id,
        api_latency_ms=round(latency, 2),
        total_count=total_count,
        page=page,
        limit=limit,
        data=[CryptoResponse.from_orm(item) for item in data]
    )

@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get ETL statistics"""
    # Total records
    total_result = await db.execute(select(func.count(CryptoCurrency.id)))
    total_records = total_result.scalar()
    
    # Records by source
    source_result = await db.execute(
        select(CryptoCurrency.source, func.count(CryptoCurrency.id))
        .group_by(CryptoCurrency.source)
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
    
    return StatsResponse(
        total_records=total_records,
        total_sources=len(records_by_source),
        last_success=last_success,
        last_failure=last_failure,
        avg_duration_seconds=round(avg_duration, 2) if avg_duration else None,
        records_by_source=records_by_source
    )

@router.post("/etl/run")
async def trigger_etl(db: AsyncSession = Depends(get_db)):
    """
    Manually trigger all ETL pipelines
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
