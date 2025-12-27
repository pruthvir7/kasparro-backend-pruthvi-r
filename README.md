
# Kasparro Backend - Cryptocurrency ETL & API

Production-grade ETL pipeline and REST API for cryptocurrency data aggregation from multiple sources.

## 🏗️ Architecture

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│ CoinPaprika │      │  CoinGecko  │      │  CSV File    │
│     API     │      │     API     │      │              │
└──────┬──────┘      └──────┬──────┘      └──────┬───────┘
       │                    │                     │
       └────────────────────┴─────────────────────┘
                            │
                    ┌───────▼────────┐
                    │   ETL Pipeline │
                    │ - Checkpoints  │
                    │ - Retry Logic  │
                    │ - Validation   │
                    │ - Drift Detect │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │  PostgreSQL    │
                    │ - Raw Tables   │
                    │ - Unified Data │
                    │ - Checkpoints  │
                    │ - ETL Metadata │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │   FastAPI      │
                    │ - /health      │
                    │ - /data        │
                    │ - /stats       │
                    │ - /metrics     │
                    └────────────────┘
```

## ✨ Features

### P0 - Core features

- Multi-source ETL (CoinPaprika, CoinGecko, CSV) into PostgreSQL
- Raw and unified tables with SQLAlchemy ORM models
- FastAPI service with `/health`, `/data`, `/stats` endpoints
- Dockerized API and database with docker-compose
- Basic pytest suite for API and ETL imports

### P1 - Advanced features

- Third data source (CSV) with the same unified schema
- Checkpoint table and ETL run tracking for recovery
- Idempotent upserts using SQLAlchemy for safe re-runs
- Stats endpoint aggregating record counts and ETL run info
- Clear separation into core, models, schemas, etl, api, utils

### P2 - Extra features

- Prometheus-compatible metrics endpoint at `/api/v1/metrics`
- Schema drift detection for upstream API changes in ETL
- In-memory rate limiting (100 requests/min per IP) with 429 responses

## 🚀 Quick start

### Prerequisites

- Docker and Docker Compose installed
- Internet access (for CoinPaprika and CoinGecko APIs)
- A CoinGecko demo API key (or environment variable placeholder)

### Setup

1. Clone the repository:

```
git clone https://github.com/yourusername/kasparro-backend-pruthvi-r.git
cd kasparro-backend-pruthvi-r
```

2. Create `.env` in the project root:

```
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/kasparro
COINGECKO_API_KEY=your_coingecko_api_key_here
ENVIRONMENT=development
EOF
```

3. Start the stack:

```
make up
```

This starts the FastAPI app on port 8000 and PostgreSQL on port 5432 inside Docker.

4. Run the ETL once to populate data:

```
make etl
```

5. Open:

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health
- Data: http://localhost:8000/api/v1/data?limit=5
- Stats: http://localhost:8000/api/v1/stats
- Metrics: http://localhost:8000/api/v1/metrics

## 📡 API endpoints

### Root

`GET /`

Simple welcome payload and link to docs.

### Health

`GET /api/v1/health`

- Checks DB connectivity with a lightweight query
- Returns latest ETL run status from `etl_runs`

Example response:

```
{
  "status": "healthy",
  "database": "connected",
  "etl_last_run": "2025-12-27T13:40:00",
  "etl_status": "success"
}
```

### Data

`GET /api/v1/data`

Query parameters:

- `coin` (optional): symbol, e.g. `BTC`
- `source` (optional): `coinpaprika`, `coingecko`, `csv`
- `page` (default 1, >=1)
- `limit` (default 20, max 100)

Example:

```
curl "http://localhost:8000/api/v1/data?coin=BTC&limit=5"
```

Response shape:

```
{
  "request_id": "uuid",
  "api_latency_ms": 15.2,
  "total_count": 200,
  "page": 1,
  "limit": 5,
  "data": [
    {
      "id": 32,
      "coin_id": "hbar-hedera-hashgraph",
      "name": "Hedera Hashgraph",
      "symbol": "HBAR",
      "price_usd": 0.11264879700254038,
      "market_cap": 4818744765.0,
      "volume_24h": 53893971.69687404,
      "source": "coinpaprika",
      "last_updated": "2025-12-27T13:39:31.639267"
    }
  ]
}
```

### Stats

`GET /api/v1/stats`

Returns ETL and data statistics aggregated from `cryptocurrencies` and `etl_runs`.

Example response:

```
{
  "total_records": 200,
  "total_sources": 3,
  "last_success": "2025-12-27T13:40:00",
  "last_failure": null,
  "avg_duration_seconds": 12.5,
  "records_by_source": {
    "coinpaprika": 100,
    "coingecko": 98,
    "csv": 2
  }
}
```

### Metrics

`GET /api/v1/metrics`

Prometheus text format with:

- `api_requests_total`
- `api_request_duration_seconds`
- `etl_runs_total`
- `etl_duration_seconds`
- `etl_records_processed_total`
- `rate_limit_exceeded_total`
- Python and process metrics via the Prometheus client

Example:

```
curl "http://localhost:8000/api/v1/metrics"
```

## 🛠️ Make targets

```
make up        # Start API + DB
make down      # Stop everything
make etl       # Run all ETL pipelines
make test      # Run pytest suite
make logs-api  # Tail API logs
make logs-db   # Tail DB logs
make clean     # Remove containers and volumes
```

These wrappers call docker-compose with the right services for consistent local runs.

## 📁 Project structure

```
kasparro-backend-pruthvi-r/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── database.py
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── base_etl.py
│   │   ├── coingecko_etl.py
│   │   ├── coinpaprika_etl.py
│   │   ├── csv_etl.py
│   │   └── run_all.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── crypto.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── metrics.py
│   │   ├── rate_limiter.py
│   │   └── schema_detector.py
│   └── main.py
├── data/
│   └── sample_crypto.csv
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api.py
│   └── test_etl.py
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── requirements.txt
├── pytest.ini
├── .env
├── .gitignore
└── README.md
```

## 🧬 ETL design

- `base_etl.py` defines an abstract **BaseETL** with `extract`, `transform`, `load`, checkpoint helpers, and ETL run tracking
- `coinpaprika_etl.py`, `coingecko_etl.py`, `csv_etl.py` subclass BaseETL and implement source-specific logic while outputting a unified schema
- `run_all.py` opens a DB session and runs all three ETL classes sequentially, collecting per-source results

Unified schema (logical):

```
{
  "coin_id": str,
  "name": str,
  "symbol": str,
  "price_usd": float,
  "market_cap": float | None,
  "volume_24h": float | None,
  "source": str,
  "last_updated": datetime
}
```

This is what is stored in the `cryptocurrencies` table and returned by `/api/v1/data`.

## 🔍 Observability and drift detection

- `metrics.py` registers Prometheus counters, histograms, and gauges used by the FastAPI middleware and ETL logic
- `rate_limiter.py` keeps an in-memory timestamp list per IP and throws HTTP 429 when the per-minute limit is exceeded, also incrementing `rate_limit_exceeded_total`
- `schema_detector.py` inspects sample API records, compares fields to expected schemas per source, logs missing/new fields, and attaches a confidence score, helping detect upstream API changes early

## 🧪 Testing

- `test_api.py` verifies the root and health endpoints return successful responses and expected shapes
- `test_etl.py` smoke-tests ETL and model imports to ensure the core modules load without errors
- `conftest.py` provides async fixtures and test DB wiring for potential future integration tests

Run:

```
make test
```

## 🔐 Configuration

Configuration is read via environment variables through `config.py`:

- `DATABASE_URL` – async SQLAlchemy URL for PostgreSQL
- `COINGECKO_API_KEY` – API key for CoinGecko demo API
- `ENVIRONMENT` – environment tag (`development`, `test`, `production`)

In Docker, these are loaded from `.env` and the docker-compose service definitions.

## 📦 Deployment notes

For local use the stack runs entirely via Docker; for cloud deployment the same image can be reused with:

- Managed PostgreSQL instance instead of the local DB container
- A scheduler (cron, cloud scheduler, or task runner) calling the ETL entrypoint on a schedule

---

**Made with ❤️ for Kasparro**
