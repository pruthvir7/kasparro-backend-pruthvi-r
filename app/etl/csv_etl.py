import pandas as pd
from app.etl.base_etl import BaseETL
from app.models.models import RawCSV


class CSVETL(BaseETL):
    def __init__(self, db_session, csv_path: str):
        super().__init__(db_session, "csv")
        self.csv_path = csv_path
    
    async def extract(self):
        """Read CSV file"""
        df = pd.read_csv(self.csv_path)
        raw_data = df.to_dict('records')
        
        # Save raw data for debugging
        await self._save_raw_data(raw_data)
        
        return raw_data
    
    async def transform(self, raw_data):
        """Transform to unified schema - BaseETL will handle normalization"""
        transformed = []
        for row in raw_data:
            transformed.append({
                'coin_id': row['coin_id'],  # CSV coin_id
                'name': row['name'],
                'symbol': row['symbol'].upper(),
                'price_usd': float(row['price_usd']),
                'market_cap': float(row['market_cap']) if pd.notna(row.get('market_cap')) else None,
                'volume_24h': float(row['volume_24h']) if pd.notna(row.get('volume_24h')) else None
            })
        return transformed
    
    async def _save_raw_data(self, raw_data):
        """Save raw data for debugging"""
        try:
            for row in raw_data:
                raw = RawCSV(
                    coin_id=row.get('coin_id', row.get('symbol', 'unknown')),
                    raw_data=row
                )
                self.db.add(raw)
            await self.db.commit()
        except Exception as e:
            logger = __import__('structlog').get_logger()
            logger.error("failed_to_save_raw_data", source="csv", error=str(e))
    
    # REMOVED load() method - BaseETL handles it with normalization
