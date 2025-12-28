FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Create startup script (NO ETL on startup for Cloud Run)
RUN echo '#!/bin/bash\n\
set -e\n\
echo "========================================"\n\
echo "Kasparro Backend Startup (Cloud Run)"\n\
echo "========================================"\n\
echo ""\n\
echo "Step 1: Creating database tables..."\n\
python -c "\
import asyncio\n\
from app.core.database import engine, Base\n\
from app.models.models import CryptoCurrency, Checkpoint, ETLRun\n\
\n\
async def init_db():\n\
    async with engine.begin() as conn:\n\
        await conn.run_sync(Base.metadata.create_all)\n\
    print(\"Tables created successfully\")\n\
\n\
asyncio.run(init_db())\n\
"\n\
echo "✓ Database initialized"\n\
echo ""\n\
echo "Note: ETL will run via Cloud Scheduler (cron)"\n\
echo ""\n\
echo "Step 2: Starting API server on port ${PORT:-8000}"\n\
echo "========================================"\n\
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Cloud Run uses PORT env variable
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:${PORT:-8000}/api/v1/health', timeout=5)" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
