from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, Index, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime


# ============================================================================
# NEW NORMALIZED SCHEMA (Core requirement for passing)
# ============================================================================

class Coin(Base):
    """
    Canonical coin entity - ONE record per cryptocurrency.
    This is the master table that unifies coins across all sources.
    """
    __tablename__ = "coins"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)  # BTC, ETH, USDT
    name = Column(String(100), nullable=False)  # Bitcoin, Ethereum, Tether
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    identifiers = relationship("CoinIdentifier", back_populates="coin", cascade="all, delete-orphan")
    prices = relationship("CoinPrice", back_populates="coin", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Coin(symbol='{self.symbol}', name='{self.name}')>"


class CoinIdentifier(Base):
    """
    Maps source-specific IDs to canonical coins.
    Example: 'btc-bitcoin' (CoinPaprika) -> BTC coin
             'bitcoin' (CoinGecko) -> BTC coin
    """
    __tablename__ = "coin_identifiers"
    
    id = Column(Integer, primary_key=True)
    coin_id = Column(Integer, ForeignKey("coins.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)  # coinpaprika, coingecko, csv
    source_id = Column(String(100), nullable=False)  # Source-specific ID
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    coin = relationship("Coin", back_populates="identifiers")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('source', 'source_id', name='uix_source_source_id'),
        Index('idx_source_source_id', 'source', 'source_id'),
    )

    def __repr__(self):
        return f"<CoinIdentifier(source='{self.source}', source_id='{self.source_id}')>"


class CoinPrice(Base):
    """
    Time-series price data linked to canonical coins.
    Multiple price records per coin (historical data).
    """
    __tablename__ = "coin_prices"
    
    id = Column(Integer, primary_key=True)
    coin_id = Column(Integer, ForeignKey("coins.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)  # Which source provided this price
    price_usd = Column(Float, nullable=False)
    market_cap = Column(Float)
    volume_24h = Column(Float)
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.datetime.utcnow)
    
    # Relationships
    coin = relationship("Coin", back_populates="prices")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_coin_timestamp', 'coin_id', 'timestamp'),
        Index('idx_coin_source_timestamp', 'coin_id', 'source', 'timestamp'),
    )

    def __repr__(self):
        return f"<CoinPrice(coin_id={self.coin_id}, price_usd={self.price_usd}, source='{self.source}')>"


# ============================================================================
# RAW DATA TABLES (Keep these - they're good for debugging)
# ============================================================================

class RawCoinPaprika(Base):
    """Raw data from CoinPaprika API"""
    __tablename__ = "raw_coinpaprika"
    
    id = Column(Integer, primary_key=True)
    coin_id = Column(String(100), unique=True)
    raw_data = Column(JSON)
    fetched_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<RawCoinPaprika(coin_id='{self.coin_id}')>"


class RawCoinGecko(Base):
    """Raw data from CoinGecko API"""
    __tablename__ = "raw_coingecko"
    
    id = Column(Integer, primary_key=True)
    coin_id = Column(String(100), unique=True)
    raw_data = Column(JSON)
    fetched_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<RawCoinGecko(coin_id='{self.coin_id}')>"


class RawCSV(Base):
    """Raw data from CSV file"""
    __tablename__ = "raw_csv"
    
    id = Column(Integer, primary_key=True)
    coin_id = Column(String(100))
    raw_data = Column(JSON)
    fetched_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<RawCSV(coin_id='{self.coin_id}')>"


# ============================================================================
# OLD SCHEMA (Keep for backward compatibility during migration)
# ============================================================================

class CryptoCurrency(Base):
    """
    DEPRECATED - This table is kept only for backward compatibility.
    New data goes into the normalized structure (Coin -> CoinPrice).
    Will be removed after migration is complete.
    """
    __tablename__ = "cryptocurrencies"
    
    id = Column(Integer, primary_key=True)
    coin_id = Column(String(100), unique=True)
    name = Column(String(100))
    symbol = Column(String(10))
    price_usd = Column(Float)
    market_cap = Column(Float)
    volume_24h = Column(Float)
    percent_change_24h = Column(Float, nullable=True)
    source = Column(String(50))
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<CryptoCurrency(symbol='{self.symbol}', source='{self.source}')>"


# ============================================================================
# ETL METADATA TABLES
# ============================================================================

class Checkpoint(Base):
    """ETL checkpoint for recovery and incremental processing"""
    __tablename__ = "checkpoints"
    
    id = Column(Integer, primary_key=True)
    source_name = Column(String(50), unique=True, nullable=False)
    last_processed_id = Column(String(100))
    last_run_timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(20))  # success, failed, running
    records_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Checkpoint(source='{self.source_name}', records={self.records_processed})>"


class ETLRun(Base):
    """ETL execution metadata for monitoring and debugging"""
    __tablename__ = "etl_runs"
    
    id = Column(Integer, primary_key=True)
    source_name = Column(String(50), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)  # success, failure, running
    records_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    def __repr__(self):
        return f"<ETLRun(source='{self.source_name}', status='{self.status}', records={self.records_processed})>"
