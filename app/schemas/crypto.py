from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Any


class CryptoBase(BaseModel):
    name: str
    symbol: str
    price_usd: float = Field(gt=0)
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    

class CryptoResponse(CryptoBase):
    """
    Cryptocurrency response schema.
    
    Compatible with both old (CryptoCurrency) and new (Coin + CoinPrice) schemas.
    """
    id: int
    coin_id: str  # Format: "source:symbol" or original coin_id
    source: str
    last_updated: datetime
    
    class Config:
        from_attributes = True
        
    @validator('last_updated', pre=True)
    def handle_timestamp(cls, v):
        """Handle both 'last_updated' and 'timestamp' field names"""
        return v


class HealthResponse(BaseModel):
    status: str
    database: str
    etl_last_run: Optional[datetime]
    etl_status: Optional[str]


class StatsResponse(BaseModel):
    """
    Statistics response schema.
    
    Updated to show both canonical coins and price records.
    """
    total_records: int  # Total price records
    total_sources: int
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    avg_duration_seconds: Optional[float]
    records_by_source: dict


class DataResponse(BaseModel):
    """
    Paginated data response.
    
    Returns cryptocurrency data with request metadata.
    """
    request_id: str
    api_latency_ms: float
    total_count: int
    page: int
    limit: int
    data: list[Any]  # Changed from list[CryptoResponse] to handle dict format


class CanonicalCoinIdentifier(BaseModel):
    """Source identifier for a canonical coin"""
    source: str
    source_id: str


class CanonicalCoinResponse(BaseModel):
    """
    NEW: Canonical coin with source mappings.
    
    Shows how a single coin is unified across multiple sources.
    """
    symbol: str
    name: str
    created_at: str
    source_identifiers: list[CanonicalCoinIdentifier]


class CanonicalCoinsResponse(BaseModel):
    """Response for /api/v1/coins endpoint"""
    total_coins: int
    coins: list[CanonicalCoinResponse]
