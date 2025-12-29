import httpx
from app.etl.base_etl import BaseETL
from app.models.models import RawCoinPaprika
from sqlalchemy.dialects.postgresql import insert


class CoinPaprikaETL(BaseETL):
    def __init__(self, db_session):
        super().__init__(db_session, "coinpaprika")
        self.base_url = "https://api.coinpaprika.com/v1"
    
    async def extract(self):
        """Fetch data from CoinPaprika API - Free tier, no auth needed"""
        
        async with httpx.AsyncClient() as client:
            response = await self.fetch_with_retry(
                lambda: client.get(
                    f"{self.base_url}/tickers",
                    params={"limit": 100}
                )
            )
            response.raise_for_status()
            
            # Save raw data for debugging
            raw_data = response.json()
            await self._save_raw_data(raw_data)
            
            return raw_data
    
    async def transform(self, raw_data):
        """Transform to unified schema - BaseETL will handle normalization"""
        transformed = []
        for coin in raw_data:
            transformed.append({
                'coin_id': coin['id'],  # CoinPaprika ID: 'btc-bitcoin'
                'name': coin['name'],
                'symbol': coin['symbol'].upper(),
                'price_usd': float(coin['quotes']['USD']['price']),
                'market_cap': float(coin['quotes']['USD']['market_cap']) if coin['quotes']['USD']['market_cap'] else None,
                'volume_24h': float(coin['quotes']['USD']['volume_24h']) if coin['quotes']['USD']['volume_24h'] else None
            })
        return transformed
    
    async def _save_raw_data(self, raw_data):
        """Save raw data for debugging"""
        try:
            for coin in raw_data:
                stmt = insert(RawCoinPaprika).values(
                    coin_id=coin['id'],
                    raw_data=coin
                ).on_conflict_do_update(
                    index_elements=['coin_id'],
                    set_={'raw_data': coin, 'fetched_at': 'NOW()'}
                )
                await self.db.execute(stmt)
            await self.db.commit()
        except Exception as e:
            logger = __import__('structlog').get_logger()
            logger.error("failed_to_save_raw_data", source="coinpaprika", error=str(e))
    
    # REMOVED load() method - BaseETL handles it with normalization
