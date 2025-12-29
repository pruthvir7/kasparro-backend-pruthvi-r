# ============================================================================
# Stage 1: Builder - Install dependencies
# ============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt


# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are in PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY app/ ./app/
COPY data/ ./data/

# Create data directory
RUN mkdir -p /app/data

# Create startup script with normalization support
RUN echo '#!/bin/bash\n\
set -e\n\
echo "========================================"\n\
echo "Kasparro Backend v2.0 (Normalized)"\n\
echo "========================================"\n\
echo ""\n\
echo "Step 1: Creating database tables..."\n\
python -c "\
import asyncio\n\
from app.core.database import engine, Base\n\
from app.models.models import (\n\
    Coin, CoinIdentifier, CoinPrice,\n\
    CryptoCurrency, Checkpoint, ETLRun,\n\
    RawCoinPaprika, RawCoinGecko, RawCSV\n\
)\n\
\n\
async def init_db():\n\
    async with engine.begin() as conn:\n\
        await conn.run_sync(Base.metadata.create_all)\n\
    print(\"✓ All tables created (including normalized schema)\")\n\
\n\
asyncio.run(init_db())\n\
"\n\
echo "✓ Database initialized"\n\
echo ""\n\
echo "Note: ETL runs via Cloud Scheduler (hourly cron)"\n\
echo "Normalization: Coins unified across sources"\n\
echo ""\n\
echo "Step 2: Starting API server on port ${PORT:-8000}"\n\
echo "========================================"\n\
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Environment variables
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/v1/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
