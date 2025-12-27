from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from datetime import datetime
from app.core.database import Base

class Checkpoint(Base):
    __tablename__ = "checkpoints"
    
    id = Column(Integer, primary_key=True)
    source_name = Column(String(50), unique=True, nullable=False)
    last_processed_id = Column(String(100))
    last_run_timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20))  # success, failed, running
    records_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

class RawCoinPaprika(Base):
    __tablename__ = "raw_coinpaprika"
    
    id = Column(Integer, primary_key=True)
    coin_id = Column(String(100), unique=True)
    raw_data = Column(JSON)
    fetched_at = Column(DateTime, default=datetime.utcnow)

class RawCoinGecko(Base):
    __tablename__ = "raw_coingecko"
    
    id = Column(Integer, primary_key=True)
    coin_id = Column(String(100), unique=True)
    raw_data = Column(JSON)
    fetched_at = Column(DateTime, default=datetime.utcnow)

class RawCSV(Base):
    __tablename__ = "raw_csv"
    
    id = Column(Integer, primary_key=True)
    coin_id = Column(String(100))
    raw_data = Column(JSON)
    fetched_at = Column(DateTime, default=datetime.utcnow)

class CryptoCurrency(Base):
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
    last_updated = Column(DateTime, default=datetime.utcnow)

class ETLRun(Base):
    __tablename__ = "etl_runs"
    
    id = Column(Integer, primary_key=True)
    source_name = Column(String(50))
    start_time = Column(DateTime)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(20))
    records_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Float, nullable=True)
