from abc import ABC, abstractmethod
from sqlalchemy import select, update
from app.models.models import Checkpoint, ETLRun
from datetime import datetime
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from app.utils.metrics import etl_runs_total, etl_duration_seconds, etl_records_processed
import time


logger = structlog.get_logger()

class BaseETL(ABC):
    def __init__(self, db_session, source_name: str):
        self.db = db_session
        self.source_name = source_name
        self.run_id = None
    
    async def get_checkpoint(self):
        """Get last checkpoint for this source"""
        result = await self.db.execute(
            select(Checkpoint).where(Checkpoint.source_name == self.source_name)
        )
        return result.scalar_one_or_none()
    
    async def update_checkpoint(self, last_id: str, records: int, status: str, error: str = None):
        """Update checkpoint after processing"""
        checkpoint = await self.get_checkpoint()
        if checkpoint:
            await self.db.execute(
                update(Checkpoint)
                .where(Checkpoint.source_name == self.source_name)
                .values(
                    last_processed_id=last_id,
                    last_run_timestamp=datetime.utcnow(),
                    status=status,
                    records_processed=records,
                    error_message=error
                )
            )
        else:
            checkpoint = Checkpoint(
                source_name=self.source_name,
                last_processed_id=last_id,
                status=status,
                records_processed=records,
                error_message=error
            )
            self.db.add(checkpoint)
        await self.db.commit()
    
    async def start_run(self):
        """Create ETL run record"""
        run = ETLRun(
            source_name=self.source_name,
            start_time=datetime.utcnow(),
            status="running"
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        self.run_id = run.id
        return run
    
    async def end_run(self, status: str, records: int, error: str = None):
        """Update ETL run record"""
        result = await self.db.execute(
            select(ETLRun).where(ETLRun.id == self.run_id)
        )
        run = result.scalar_one()
        run.end_time = datetime.utcnow()
        run.status = status
        run.records_processed = records
        run.error_message = error
        run.duration_seconds = (run.end_time - run.start_time).total_seconds()
        await self.db.commit()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_with_retry(self, fetch_func):
        """Fetch data with exponential backoff"""
        return await fetch_func()
    
    @abstractmethod
    async def extract(self):
        """Extract data from source"""
        pass
    
    @abstractmethod
    async def transform(self, raw_data):
        """Transform data to unified schema"""
        pass
    
    @abstractmethod
    async def load(self, transformed_data):
        """Load data into database"""
        pass
    
    async def run(self):
        """Execute full ETL pipeline"""
        logger.info("etl_started", source=self.source_name)
        await self.start_run()
        
        start_time = time.time()
        
        try:
            # Extract
            raw_data = await self.extract()
            logger.info("extract_complete", source=self.source_name, count=len(raw_data))
            
            # Transform
            transformed_data = await self.transform(raw_data)
            logger.info("transform_complete", source=self.source_name, count=len(transformed_data))
            
            # Load
            await self.load(transformed_data)
            logger.info("load_complete", source=self.source_name, count=len(transformed_data))
            
            # Update checkpoint
            last_id = transformed_data[-1].get('coin_id') if transformed_data else None
            await self.update_checkpoint(last_id, len(transformed_data), "success")
            await self.end_run("success", len(transformed_data))
            
            # Track metrics
            duration = time.time() - start_time
            etl_runs_total.labels(source=self.source_name, status="success").inc()
            etl_duration_seconds.labels(source=self.source_name).observe(duration)
            etl_records_processed.labels(source=self.source_name).inc(len(transformed_data))
            
            return len(transformed_data)
            
        except Exception as e:
            logger.error("etl_failed", source=self.source_name, error=str(e))
            await self.update_checkpoint(None, 0, "failed", str(e))
            await self.end_run("failed", 0, str(e))
            
            # Track failure
            etl_runs_total.labels(source=self.source_name, status="failed").inc()
            
            raise

