import asyncio
from app.core.database import async_session_maker
from app.etl.coinpaprika_etl import CoinPaprikaETL
from app.etl.coingecko_etl import CoinGeckoETL
from app.etl.csv_etl import CSVETL
import structlog

logger = structlog.get_logger()

async def run_all_etls():
    """Run all ETL pipelines"""
    async with async_session_maker() as session:
        etls = [
            CoinPaprikaETL(session),
            CoinGeckoETL(session),
            CSVETL(session, "/app/data/sample_crypto.csv")
        ]
        
        results = []
        for etl in etls:
            try:
                count = await etl.run()
                results.append((etl.source_name, count, "success"))
            except Exception as e:
                logger.error("etl_error", source=etl.source_name, error=str(e))
                results.append((etl.source_name, 0, "failed"))
        
        logger.info("all_etls_complete", results=results)
        return results

if __name__ == "__main__":
    asyncio.run(run_all_etls())
