# Kasparro Backend - Deployment Guide for Evaluators

## System Overview

Production-grade ETL pipeline and REST API for cryptocurrency data aggregation.

**Technology Stack:**
- FastAPI (Python 3.11)
- PostgreSQL with async driver (asyncpg)
- Docker & Docker Compose
- Prometheus metrics
- Structured logging (structlog)

---

## Prerequisites

- Docker Desktop or Docker Engine (20.10+)
- Docker Compose (v2.0+)
- Internet connection (for CoinGecko & CoinPaprika APIs)
- CoinGecko API key (free tier: https://www.coingecko.com/en/api)

---

## Local Deployment (Docker)

### Step 1: Clone Repository

```
git clone https://github.com/pruthvir7/kasparro-backend-pruthvi-r.git
cd kasparro-backend-pruthvi-r
```

### Step 2: Configure Environment

```
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env  # or use your preferred editor
```

**Required variables in `.env`:**
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/kasparro
COINGECKO_API_KEY=your_actual_coingecko_api_key_here
API_KEY=kasparro_secret_key_2025
ENVIRONMENT=development
```

### Step 3: Start System

```
docker-compose up --build
```

**Expected startup sequence (60-90 seconds):**
```
========================================
Kasparro Backend Startup
========================================

Step 1: Creating database tables...
Tables created successfully
✓ Database initialized

Step 2: Running ETL pipelines...
[ETL logs: CoinPaprika, CoinGecko, CSV]
✓ ETL complete

Step 3: Starting API server on port 8000
========================================
INFO:     Started server process
```

**Wait for:** `Started server process` message before testing.

### Step 4: Verify Installation

#### Health Check
```
curl http://localhost:8000/api/v1/health
```

**Expected response:**
```
{
  "status": "healthy",
  "database": "connected",
  "etl_last_run": "2025-12-28T...",
  "etl_status": "success"
}
```

#### API Documentation
Open browser: http://localhost:8000/docs

#### Test Data Endpoint (requires authentication)
```
curl -H "X-API-Key: kasparro_secret_key_2025" \
  "http://localhost:8000/api/v1/data?limit=5"
```

**Expected:** JSON array with 5 cryptocurrency records.

#### Test Statistics
```
curl -H "X-API-Key: kasparro_secret_key_2025" \
  http://localhost:8000/api/v1/stats
```

**Expected:** Shows ~200 total records across 3 sources.

---

## API Authentication

All data endpoints require authentication header:

```
X-API-Key: kasparro_secret_key_2025
```

**Public endpoints (no auth):**
- `GET /api/v1/health`
- `GET /api/v1/metrics`
- `GET /` (root)

**Protected endpoints (require auth):**
- `GET /api/v1/data`
- `GET /api/v1/stats`
- `POST /api/v1/etl/run`

**Test authentication:**
```
# Without auth (should fail)
curl http://localhost:8000/api/v1/data
# Response: 403 Forbidden

# With auth (should succeed)
curl -H "X-API-Key: kasparro_secret_key_2025" \
  http://localhost:8000/api/v1/data?limit=1
# Response: 200 OK with data
```

---

## Running Tests

### Automated Test Suite

```
# Run all 17 tests
pytest -v

# Run specific test categories
pytest tests/test_etl_comprehensive.py -v  # ETL tests
pytest tests/test_api_comprehensive.py -v  # API tests
```

**Expected output:**
```
17 passed in 2.15s
```

**Test coverage:**
- ✅ ETL extraction, transformation, loading
- ✅ Incremental ingestion (no duplicates)
- ✅ Checkpoint creation and tracking
- ✅ Multiple data source handling
- ✅ API authentication
- ✅ API validation and error handling

### Tests Inside Docker

```
docker-compose exec api pytest -v
```

---

## Manual ETL Trigger

ETL runs automatically on startup. To trigger manually:

```
curl -X POST \
  -H "X-API-Key: kasparro_secret_key_2025" \
  http://localhost:8000/api/v1/etl/run
```

**Response shows results per source:**
```
{
  "status": "success",
  "message": "ETL pipelines completed",
  "results": [
    {"source": "coinpaprika", "records": 100, "status": "success"},
    {"source": "coingecko", "records": 98, "status": "success"},
    {"source": "csv", "records": 2, "status": "success"}
  ]
}
```

---

## Monitoring & Observability

### Prometheus Metrics

```
curl http://localhost:8000/api/v1/metrics
```

**Available metrics:**
- `api_requests_total` - Total API requests by endpoint
- `api_request_duration_seconds` - Request latency histogram
- `etl_runs_total` - ETL executions by source and status
- `etl_duration_seconds` - ETL runtime histogram
- `etl_records_processed_total` - Records loaded per source
- `rate_limit_exceeded_total` - Rate limit violations

### Logs

```
# View API logs
docker-compose logs -f api

# View database logs
docker-compose logs -f db

# View last 100 lines
docker-compose logs --tail=100 api
```

---

## API Endpoints Reference

### GET /api/v1/health
**Auth:** None required  
**Returns:** System health, database status, last ETL run

### GET /api/v1/data
**Auth:** Required  
**Query params:**
- `coin` (optional): Filter by symbol (e.g., BTC, ETH)
- `source` (optional): Filter by source (coinpaprika, coingecko, csv)
- `page` (default: 1, min: 1)
- `limit` (default: 20, min: 1, max: 100)

**Example:**
```
curl -H "X-API-Key: kasparro_secret_key_2025" \
  "http://localhost:8000/api/v1/data?coin=BTC&limit=10"
```

### GET /api/v1/stats
**Auth:** Required  
**Returns:** ETL statistics, record counts by source, run history

### GET /api/v1/metrics
**Auth:** None required  
**Returns:** Prometheus metrics (plain text format)

### POST /api/v1/etl/run
**Auth:** Required  
**Returns:** ETL execution results for all sources

---

## Troubleshooting

### Issue: "relation 'etl_runs' does not exist"

**Cause:** Database tables not created  
**Solution:**
```
docker-compose down -v  # Remove volumes
docker-compose up --build  # Rebuild and restart
```

### Issue: Port 8000 already in use

**Solution 1:** Stop conflicting service  
**Solution 2:** Change port in `docker-compose.yml`:
```
ports:
  - "8001:8000"  # Use 8001 instead
```

### Issue: ETL fails with API errors

**Cause:** Invalid or missing API keys  
**Solution:** Verify `.env` file has valid `COINGECKO_API_KEY`

### Issue: Tests fail with "aiosqlite not found"

**Solution:**
```
pip install aiosqlite==0.19.0
pytest -v
```

### Issue: Docker build fails

**Solution:**
```
docker-compose down
docker system prune -a  # Clean Docker cache
docker-compose up --build
```

---

## Stopping the System

```
# Stop containers (data persists)
docker-compose down

# Stop and remove all data
docker-compose down -v
```

---

## Production Deployment

**Cloud deployment:** [Your Render/AWS URL]

**Deployment documentation:** See README.md for cloud-specific setup.

---

## Architecture

```
Data Sources → ETL Pipeline → PostgreSQL → FastAPI → Clients
    ↓              ↓              ↓           ↓
CoinPaprika    Extract      Raw Tables   /health
CoinGecko      Transform    Unified      /data
CSV File       Load         Checkpoints  /stats
                            ETL Runs     /metrics
```

**Data Flow:**
1. ETL extracts from 3 sources
2. Transforms to unified schema
3. Loads into PostgreSQL (idempotent upserts)
4. Creates checkpoints for recovery
5. Tracks runs in metadata table
6. API exposes data via REST endpoints

---

## Support

For issues or questions, refer to:
- Main documentation: `README.md`
- Test suite: `tests/`
- API documentation: http://localhost:8000/docs (when running)

**Project repository:** https://github.com/pruthvir7/kasparro-backend-pruthvi-r

