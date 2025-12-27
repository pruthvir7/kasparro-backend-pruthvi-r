from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional

class CryptoBase(BaseModel):
    name: str
    symbol: str
    price_usd: float = Field(gt=0)
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    
class CryptoResponse(CryptoBase):
    id: int
    coin_id: str
    source: str
    last_updated: datetime
    
    class Config:
        from_attributes = True

class HealthResponse(BaseModel):
    status: str
    database: str
    etl_last_run: Optional[datetime]
    etl_status: Optional[str]

class StatsResponse(BaseModel):
    total_records: int
    total_sources: int
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    avg_duration_seconds: Optional[float]
    records_by_source: dict

class DataResponse(BaseModel):
    request_id: str
    api_latency_ms: float
    total_count: int
    page: int
    limit: int
    data: list[CryptoResponse]
