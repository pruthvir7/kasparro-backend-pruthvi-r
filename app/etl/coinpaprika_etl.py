import httpx
from app.etl.base_etl import BaseETL
from app.models.models import RawCoinPaprika, CryptoCurrency
from app.core.config import settings
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert


class CoinPaprikaETL(BaseETL):
    def __init__(self, db_session):
        super().__init__(db_session, "coinpaprika")
        self.base_url = "https://api.coinpaprika.com/v1"
    
    async def extract(self):
        """Fetch data from CoinPaprika API - Free tier, no auth needed"""
        
        async with httpx.AsyncClient() as client:
            # No headers needed for free tier
            response = await self.fetch_with_retry(
                lambda: client.get(
                    f"{self.base_url}/tickers",
                    params={"limit": 100}
                )
            )
            response.raise_for_status()
            return response.json()
    
    async def transform(self, raw_data):
        """Transform to unified schema"""
        transformed = []
        for coin in raw_data:
            transformed.append({
                'coin_id': coin['id'],
                'name': coin['name'],
                'symbol': coin['symbol'],
                'price_usd': float(coin['quotes']['USD']['price']),
                'market_cap': float(coin['quotes']['USD']['market_cap']) if coin['quotes']['USD']['market_cap'] else None,
                'volume_24h': float(coin['quotes']['USD']['volume_24h']) if coin['quotes']['USD']['volume_24h'] else None,
                'percent_change_24h': float(coin['quotes']['USD']['percent_change_24h']) if coin['quotes']['USD']['percent_change_24h'] else None,
                'source': 'coinpaprika'
            })
        return transformed
    
    async def load(self, transformed_data):
        """Load into database (raw + normalized)"""
        # Save raw data
        for item in transformed_data:
            stmt = insert(RawCoinPaprika).values(
                coin_id=item['coin_id'],
                raw_data=item
            ).on_conflict_do_update(
                index_elements=['coin_id'],
                set_={'raw_data': item}
            )
            await self.db.execute(stmt)
        
        # Save normalized data
        for item in transformed_data:
            stmt = insert(CryptoCurrency).values(**item).on_conflict_do_update(
                index_elements=['coin_id'],
                set_=item
            )
            await self.db.execute(stmt)
        
        await self.db.commit()
