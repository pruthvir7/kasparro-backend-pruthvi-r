"""
Coin normalization logic - unifies coin identities across multiple data sources.

This module ensures that BTC from CoinPaprika and BTC from CoinGecko are treated
as the SAME Bitcoin entity, not as separate coins.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Coin, CoinIdentifier
import logging

logger = logging.getLogger(__name__)


class CoinNormalizer:
    """
    Normalizes coin identities across multiple data sources using symbol as canonical key.
    
    Strategy:
    1. Use symbol (BTC, ETH) as the primary identifier
    2. Map source-specific IDs to canonical coins via CoinIdentifier table
    3. Cache lookups to minimize database queries
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._coin_cache = {}  # symbol -> Coin
        self._identifier_cache = {}  # (source, source_id) -> Coin
    
    async def get_or_create_coin(
        self, 
        symbol: str, 
        name: str, 
        source: str, 
        source_id: str
    ) -> Coin:
        """
        Get or create a canonical coin entity and ensure identifier mapping exists.
        
        Args:
            symbol: Ticker symbol (BTC, ETH) - used as canonical key
            name: Full name (Bitcoin, Ethereum)
            source: Data source (coinpaprika, coingecko, csv)
            source_id: Source-specific ID (btc-bitcoin, bitcoin, etc.)
            
        Returns:
            Canonical Coin object
            
        Example:
            coin = await normalizer.get_or_create_coin(
                symbol='BTC',
                name='Bitcoin',
                source='coinpaprika',
                source_id='btc-bitcoin'
            )
            # Returns the same coin for symbol='BTC' from any source
        """
        symbol = symbol.upper().strip()
        
        # 1. Check memory cache first (fastest)
        if symbol in self._coin_cache:
            coin = self._coin_cache[symbol]
            await self._ensure_identifier(coin, source, source_id)
            return coin
        
        # 2. Check if we already mapped this source_id
        cache_key = (source, source_id)
        if cache_key in self._identifier_cache:
            coin = self._identifier_cache[cache_key]
            self._coin_cache[symbol] = coin  # Update symbol cache too
            return coin
        
        # 3. Check database for existing coin by symbol
        result = await self.session.execute(
            select(Coin).where(Coin.symbol == symbol)
        )
        coin = result.scalar_one_or_none()
        
        if not coin:
            # 4. Create new canonical coin
            coin = Coin(symbol=symbol, name=name)
            self.session.add(coin)
            await self.session.flush()  # Get ID without committing
            logger.info(f"✓ Created new canonical coin: {symbol} ({name})")
        else:
            logger.debug(f"Found existing coin: {symbol}")
        
        # 5. Ensure identifier mapping exists
        await self._ensure_identifier(coin, source, source_id)
        
        # 6. Cache for future lookups
        self._coin_cache[symbol] = coin
        self._identifier_cache[cache_key] = coin
        
        return coin
    
    async def _ensure_identifier(self, coin: Coin, source: str, source_id: str):
        """
        Ensure CoinIdentifier exists for this source-specific ID.
        This creates the mapping: source_id -> canonical coin
        """
        result = await self.session.execute(
            select(CoinIdentifier).where(
                CoinIdentifier.source == source,
                CoinIdentifier.source_id == source_id
            )
        )
        identifier = result.scalar_one_or_none()
        
        if not identifier:
            identifier = CoinIdentifier(
                coin_id=coin.id,
                source=source,
                source_id=source_id
            )
            self.session.add(identifier)
            logger.debug(f"Mapped {source}:{source_id} -> {coin.symbol}")
        
        # Cache this mapping
        self._identifier_cache[(source, source_id)] = coin
    
    async def find_coin_by_source_id(self, source: str, source_id: str) -> Coin | None:
        """
        Find canonical coin by source-specific ID.
        
        Example:
            coin = await normalizer.find_coin_by_source_id('coinpaprika', 'btc-bitcoin')
            # Returns the canonical BTC coin
        """
        cache_key = (source, source_id)
        
        # Check cache first
        if cache_key in self._identifier_cache:
            return self._identifier_cache[cache_key]
        
        # Query database
        result = await self.session.execute(
            select(Coin)
            .join(CoinIdentifier)
            .where(
                CoinIdentifier.source == source,
                CoinIdentifier.source_id == source_id
            )
        )
        coin = result.scalar_one_or_none()
        
        if coin:
            self._identifier_cache[cache_key] = coin
            self._coin_cache[coin.symbol] = coin
        
        return coin
    
    def clear_cache(self):
        """Clear in-memory caches (useful between ETL runs)"""
        self._coin_cache.clear()
        self._identifier_cache.clear()
        logger.debug("Cleared normalizer cache")
