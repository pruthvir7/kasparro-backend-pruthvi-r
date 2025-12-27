import httpx
from app.etl.base_etl import BaseETL
from app.models.models import RawCoinGecko, CryptoCurrency
from app.core.config import settings
from sqlalchemy.dialects.postgresql import insert

class CoinGeckoETL(BaseETL):
    def __init__(self, db_session):
        super().__init__(db_session, "coingecko")
        self.api_key = settings.COINGECKO_API_KEY
        self.base_url = "https://api.coingecko.com/api/v3"
    
    async def extract(self):
        """Fetch data from CoinGecko API"""
        headers = {"x-cg-demo-api-key": self.api_key}
        
        async with httpx.AsyncClient() as client:
            response = await self.fetch_with_retry(
                lambda: client.get(
                    f"{self.base_url}/coins/markets",
                    headers=headers,
                    params={"vs_currency": "usd", "per_page": 100, "page": 1}
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
                'symbol': coin['symbol'].upper(),
                'price_usd': float(coin['current_price']),
                'market_cap': float(coin['market_cap']) if coin['market_cap'] else None,
                'volume_24h': float(coin['total_volume']) if coin['total_volume'] else None,
                'percent_change_24h': float(coin['price_change_percentage_24h']) if coin['price_change_percentage_24h'] else None,
                'source': 'coingecko'
            })
        return transformed
    
    async def load(self, transformed_data):
        """Load into database"""
        for item in transformed_data:
            stmt = insert(RawCoinGecko).values(
                coin_id=item['coin_id'],
                raw_data=item
            ).on_conflict_do_update(
                index_elements=['coin_id'],
                set_={'raw_data': item}
            )
            await self.db.execute(stmt)
        
        for item in transformed_data:
            stmt = insert(CryptoCurrency).values(**item).on_conflict_do_update(
                index_elements=['coin_id'],
                set_=item
            )
            await self.db.execute(stmt)
        
        await self.db.commit()
