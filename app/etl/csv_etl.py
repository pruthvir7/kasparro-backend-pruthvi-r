import pandas as pd
from app.etl.base_etl import BaseETL
from app.models.models import RawCSV, CryptoCurrency
from sqlalchemy.dialects.postgresql import insert

class CSVETL(BaseETL):
    def __init__(self, db_session, csv_path: str):
        super().__init__(db_session, "csv")
        self.csv_path = csv_path
    
    async def extract(self):
        """Read CSV file"""
        df = pd.read_csv(self.csv_path)
        return df.to_dict('records')
    
    async def transform(self, raw_data):
        """Transform to unified schema"""
        transformed = []
        for row in raw_data:
            transformed.append({
                'coin_id': row['coin_id'],
                'name': row['name'],
                'symbol': row['symbol'],
                'price_usd': float(row['price_usd']),
                'market_cap': float(row['market_cap']) if pd.notna(row.get('market_cap')) else None,
                'volume_24h': float(row['volume_24h']) if pd.notna(row.get('volume_24h')) else None,
                'percent_change_24h': None,
                'source': 'csv'
            })
        return transformed
    
    async def load(self, transformed_data):
        """Load into database"""
        for item in transformed_data:
            raw = RawCSV(coin_id=item['coin_id'], raw_data=item)
            self.db.add(raw)
        
        for item in transformed_data:
            stmt = insert(CryptoCurrency).values(**item).on_conflict_do_update(
                index_elements=['coin_id'],
                set_=item
            )
            await self.db.execute(stmt)
        
        await self.db.commit()
