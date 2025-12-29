"""
Migration helper to move data from old schema to new normalized schema
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import CryptoCurrency, Coin, CoinIdentifier, CoinPrice
from app.utils.coin_normalizer import CoinNormalizer
import logging

logger = logging.getLogger(__name__)


async def migrate_old_data(session: AsyncSession):
    """
    Migrate data from old cryptocurrencies table to new normalized structure.
    This is idempotent - safe to run multiple times.
    """
    logger.info("Starting migration from old schema to normalized schema...")
    
    normalizer = CoinNormalizer(session)
    
    # Get all old records
    result = await session.execute(select(CryptoCurrency))
    old_records = result.scalars().all()
    
    migrated = 0
    skipped = 0
    
    for record in old_records:
        try:
            # Get or create canonical coin
            coin = await normalizer.get_or_create_coin(
                symbol=record.symbol,
                name=record.name,
                source=record.source,
                source_id=record.coin_id
            )
            
            # Create price record
            price = CoinPrice(
                coin_id=coin.id,
                source=record.source,
                price_usd=record.price_usd,
                market_cap=record.market_cap,
                volume_24h=record.volume_24h,
                timestamp=record.last_updated
            )
            session.add(price)
            migrated += 1
            
        except Exception as e:
            logger.error(f"Failed to migrate {record.symbol}: {e}")
            skipped += 1
            continue
    
    await session.commit()
    logger.info(f"Migration complete: {migrated} migrated, {skipped} skipped")
    
    return {"migrated": migrated, "skipped": skipped}
