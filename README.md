# Kasparro Backend - Cryptocurrency ETL & API

Production-grade ETL pipeline and REST API for cryptocurrency data aggregation from multiple sources.

## 🌐 Live Deployment

### GCP Cloud Run (Primary)
**Production URL:** https://kasparro-api-nk6gux63sq-el.a.run.app

**Try the API:**
- Interactive Docs: https://kasparro-api-nk6gux63sq-el.a.run.app/docs
- Health Check: https://kasparro-api-nk6gux63sq-el.a.run.app/api/v1/health
- Statistics: https://kasparro-api-nk6gux63sq-el.a.run.app/api/v1/stats

**API Key Required for Data Endpoints:**
```
curl -H "X-API-Key: kasparro_secret_key_2025" \
  "https://kasparro-api-nk6gux63sq-el.a.run.app/api/v1/data?limit=5"
```

### Cloud Infrastructure
- **Cloud Run:** FastAPI service (auto-scaling)
- **Cloud SQL:** PostgreSQL 15 database
- **Cloud Scheduler:** Automated hourly ETL cron jobs
- **Region:** asia-south1 (Mumbai)

**📚 Full deployment documentation:** [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Google Cloud Platform                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐         ┌──────────────────┐          │
│  │ Cloud Scheduler │────────▶│   Cloud Run      │          │
│  │  (Hourly Cron)  │  POST   │  (FastAPI App)   │          │
│  │  0 * * * *      │         │                  │          │
│  └─────────────────┘         └────────┬─────────┘          │
│                                        │                     │
│                                        │ Unix Socket         │
│                                        │                     │
│                               ┌────────▼─────────┐          │
│                               │   Cloud SQL      │          │
│                               │  (PostgreSQL 15) │          │
│                               └──────────────────┘          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
        ┌───────────────────┴────────────────────┐
        │                                         │
┌───────▼────────┐  ┌─────────────┐  ┌──────────▼─────┐
│  CoinPaprika   │  │  CoinGecko  │  │  CSV File      │
│      API       │  │     API     │  │                │
└────────────────┘  └─────────────┘  └────────────────┘
```

**Data Flow:**
1. Cloud Scheduler triggers ETL hourly via POST to `/api/v1/etl/run`
2. ETL extracts from 3 sources (CoinPaprika, CoinGecko, CSV)
3. Transforms to unified schema with validation
4. Loads into Cloud SQL PostgreSQL (idempotent upserts)
5. Creates checkpoints and tracks runs in metadata tables
6. FastAPI exposes data via authenticated REST endpoints

---

## ✨ Features

### Core Requirements (P0) ✅
- ✅ Multi-source ETL (CoinPaprika, CoinGecko, CSV) into PostgreSQL
- ✅ Raw and unified tables with SQLAlchemy ORM models
- ✅ FastAPI service with `/health`, `/data`, `/stats` endpoints
- ✅ Dockerized API and database with docker-compose
- ✅ Comprehensive pytest suite (17 tests)
- ✅ API Key authentication on data endpoints
- ✅ Cloud deployment with automated cron jobs (GCP)

### Advanced Features (P1) ✅
- ✅ Third data source (CSV) with unified schema
- ✅ Checkpoint table and ETL run tracking for recovery
- ✅ Idempotent upserts using SQLAlchemy for safe re-runs
- ✅ Stats endpoint aggregating record counts and ETL run info
- ✅ Clear separation: core, models, schemas, etl, api, utils
- ✅ Automated smoke test script (14 end-to-end tests)

### Extra Features (P2) ✅
- ✅ Prometheus-compatible metrics endpoint at `/api/v1/metrics`
- ✅ Schema drift detection for upstream API changes
- ✅ In-memory rate limiting (100 requests/min per IP) with 429 responses
- ✅ Structured logging with request IDs
- ✅ Cloud Scheduler for automated ETL execution
- ✅ Cloud logging and monitoring dashboards

---

## 🚀 Quick Start

### Cloud Deployment (Recommended for Evaluation)

**The system is already deployed and running!**

Test the live API:
```
# Health check
curl https://kasparro-api-nk6gux63sq-el.a.run.app/api/v1/health

# Get data (requires API key)
curl -H "X-API-Key: kasparro_secret_key_2025" \
  "https://kasparro-api-nk6gux63sq-el.a.run.app/api/v1/data?limit=5"

# View statistics
curl -H "X-API-Key: kasparro_secret_key_2025" \
  "https://kasparro-api-nk6gux63sq-el.a.run.app/api/v1/stats"
```

**View Cloud Resources:**
- [Cloud Scheduler (Cron Jobs)](https://console.cloud.google.com/cloudscheduler?project=forward-logic-482607-k3)
- [Cloud Run Logs](https://console.cloud.google.com/run/detail/asia-south1/kasparro-api/logs?project=forward-logic-482607-k3)
- [API Documentation](https://kasparro-api-nk6gux63sq-el.a.run.app/docs)

---

### Local Deployment (Docker)

**Prerequisites:**
- Docker and Docker Compose installed
- Internet access (for API data sources)
- CoinGecko API key (free tier)

**Setup:**

1. Clone the repository:
```
git clone https://github.com/pruthvir7/kasparro-backend-pruthvi-r.git
cd kasparro-backend-pruthvi-r
```

2. Create `.env` file:
```
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/kasparro
COINGECKO_API_KEY=your_coingecko_api_key_here
API_KEY=kasparro_secret_key_2025
ENVIRONMENT=development
EOF
```

3. Start the system:
```
docker-compose up --build
```

**Wait 60-90 seconds for:**
- Database initialization
- Automatic ETL execution
- API server startup

4. Test locally:
```
# Run comprehensive smoke test (14 tests)
./smoke_test.sh

# Or test manually
curl http://localhost:8000/api/v1/health
curl -H "X-API-Key: kasparro_secret_key_2025" \
  "http://localhost:8000/api/v1/data?limit=5"
```

**📚 Full local deployment guide:** [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📡 API Endpoints

### Public Endpoints (No Authentication)

#### Root
`GET /`

Welcome message and API information.

#### Health Check
`GET /api/v1/health`

Returns system health, database status, and last ETL run:
```
{
  "status": "healthy",
  "database": "connected",
  "etl_last_run": "2025-12-28T09:00:00",
  "etl_status": "success"
}
```

#### Metrics
`GET /api/v1/metrics`

Prometheus-format metrics for monitoring.

---

### Protected Endpoints (API Key Required)

**Authentication Header:**
```
X-API-Key: kasparro_secret_key_2025
```

#### Get Cryptocurrency Data
`GET /api/v1/data`

**Query Parameters:**
- `coin` (optional): Filter by symbol (e.g., `BTC`, `ETH`)
- `source` (optional): Filter by source (`coinpaprika`, `coingecko`, `csv`)
- `page` (default: 1, min: 1)
- `limit` (default: 20, min: 1, max: 100)

**Example:**
```
curl -H "X-API-Key: kasparro_secret_key_2025" \
  "https://kasparro-api-nk6gux63sq-el.a.run.app/api/v1/data?coin=BTC&limit=5"
```

**Response:**
```
{
  "request_id": "uuid",
  "api_latency_ms": 15.2,
  "total_count": 200,
  "page": 1,
  "limit": 5,
  "data": [
    {
      "id": 1,
      "coin_id": "btc-bitcoin",
      "name": "Bitcoin",
      "symbol": "BTC",
      "price_usd": 43250.50,
      "market_cap": 850000000000,
      "volume_24h": 28000000000,
      "source": "coinpaprika",
      "last_updated": "2025-12-28T09:00:00"
    }
  ]
}
```

#### Get Statistics
`GET /api/v1/stats`

Returns ETL statistics and data source breakdown:
```
{
  "total_records": 200,
  "total_sources": 3,
  "last_success": "2025-12-28T09:00:00",
  "last_failure": null,
  "avg_duration_seconds": 12.5,
  "records_by_source": {
    "coinpaprika": 100,
    "coingecko": 98,
    "csv": 2
  }
}
```

#### Trigger ETL Manually
`POST /api/v1/etl/run`

Manually triggers all ETL pipelines:
```
curl -X POST -H "X-API-Key: kasparro_secret_key_2025" \
  "https://kasparro-api-nk6gux63sq-el.a.run.app/api/v1/etl/run"
```

**Response:**
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

## 🧪 Testing

### Automated Test Suite

```
# Run all 17 tests
pytest -v

# Run specific categories
pytest tests/test_etl_comprehensive.py -v  # ETL tests
pytest tests/test_api_comprehensive.py -v  # API tests
```

**Test Coverage:**
- ✅ ETL extraction, transformation, loading
- ✅ Incremental ingestion (no duplicates)
- ✅ Checkpoint creation and tracking
- ✅ Multiple data source handling
- ✅ API authentication and authorization
- ✅ Input validation and error handling
- ✅ Rate limiting

### Smoke Test (End-to-End)

```
# Run comprehensive smoke test (14 tests)
./smoke_test.sh
```

**Tests:**
1. API server running
2. System health check
3. ETL execution verification
4. Authentication blocking
5. Valid API key acceptance
6. Data endpoint returns records
7. Statistics endpoint
8. Prometheus metrics
9. Coin filtering (BTC)
10. Pagination
11. Input validation
12. Rate limiting (100 req/min)
13. Manual ETL trigger
14. API documentation accessibility

---

## 📁 Project Structure

```
kasparro-backend-pruthvi-r/
├── app/
│   ├── api/
│   │   └── endpoints.py          # FastAPI route handlers
│   ├── core/
│   │   ├── config.py             # Environment configuration
│   │   └── database.py           # SQLAlchemy setup
│   ├── etl/
│   │   ├── base_etl.py           # Abstract ETL base class
│   │   ├── coingecko_etl.py      # CoinGecko pipeline
│   │   ├── coinpaprika_etl.py    # CoinPaprika pipeline
│   │   ├── csv_etl.py            # CSV file pipeline
│   │   └── run_all.py            # ETL orchestrator
│   ├── models/
│   │   └── models.py             # SQLAlchemy ORM models
│   ├── schemas/
│   │   └── crypto.py             # Pydantic schemas
│   ├── utils/
│   │   ├── metrics.py            # Prometheus metrics
│   │   ├── rate_limiter.py       # Rate limiting logic
│   │   └── schema_detector.py    # Drift detection
│   └── main.py                   # FastAPI application
├── data/
│   └── sample_crypto.csv         # Sample CSV data source
├── tests/
│   ├── conftest.py               # Test fixtures
│   ├── test_api_comprehensive.py # API tests
│   └── test_etl_comprehensive.py # ETL tests
├── docker-compose.yml            # Local Docker setup
├── Dockerfile                    # Container image
├── requirements.txt              # Python dependencies
├── smoke_test.sh                 # End-to-end test script
├── DEPLOYMENT.md                 # Local deployment guide
├── CLOUD_DEPLOYMENT.md           # GCP deployment guide
└── README.md                     # This file
```

---

## 🔍 Observability

### Prometheus Metrics

Access at `/api/v1/metrics`:

**API Metrics:**
- `api_requests_total` - Total requests by endpoint and status
- `api_request_duration_seconds` - Request latency histogram

**ETL Metrics:**
- `etl_runs_total` - ETL executions by source and status
- `etl_duration_seconds` - ETL runtime histogram
- `etl_records_processed_total` - Records loaded per source

**Rate Limiting:**
- `rate_limit_exceeded_total` - Rate limit violations by IP

### Logging

Structured JSON logs with:
- Request IDs for tracing
- Timestamps and severity levels
- ETL execution details
- Error stack traces

**View logs:**
```
# Local Docker
docker-compose logs -f api

# GCP Cloud Run
gcloud run services logs read kasparro-api --region=asia-south1 --limit=100
```

### Schema Drift Detection

Automatically detects changes in upstream API schemas:
- Compares actual vs expected fields
- Logs missing/new fields
- Confidence scoring
- Helps prevent ETL failures

---

## 🔐 Security

- ✅ API Key authentication on all data endpoints
- ✅ Rate limiting (100 requests/min per IP)
- ✅ HTTPS enforced (Cloud Run)
- ✅ Database accessible only via Cloud Run (Unix socket)
- ✅ Service accounts with minimal permissions
- ✅ Environment variables for secrets
- ✅ Input validation on all endpoints
- ✅ SQL injection prevention (SQLAlchemy ORM)

---

## 📊 Data Schema

### Unified Cryptocurrency Schema

```
{
  "coin_id": str,        # Unique identifier
  "name": str,           # Full name (e.g., "Bitcoin")
  "symbol": str,         # Ticker symbol (e.g., "BTC")
  "price_usd": float,    # Current price in USD
  "market_cap": float,   # Market capitalization (optional)
  "volume_24h": float,   # 24h trading volume (optional)
  "source": str,         # Data source (coinpaprika/coingecko/csv)
  "last_updated": datetime  # Last update timestamp
}
```

### Database Tables

**cryptocurrencies** - Unified crypto data  
**etl_runs** - ETL execution metadata  
**checkpoints** - ETL recovery checkpoints  

---

## 🛠️ Development

### Local Commands

```
# Start system
docker-compose up --build

# Run tests
pytest -v

# Run smoke test
./smoke_test.sh

# View logs
docker-compose logs -f api

# Stop system
docker-compose down

# Clean everything
docker-compose down -v
```

### Cloud Commands

```
# Deploy to Cloud Run
gcloud run deploy kasparro-api --source . --region=asia-south1

# View logs
gcloud run services logs read kasparro-api --region=asia-south1

# Trigger cron manually
gcloud scheduler jobs run kasparro-etl-hourly --location=asia-south1

# View cron jobs
gcloud scheduler jobs list --location=asia-south1
```

---

## 📚 Documentation

- **[README.md](README.md)** - This file (project overview)
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Local Docker deployment guide
- **[CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md)** - GCP cloud deployment guide
- **[API Docs](https://kasparro-api-nk6gux63sq-el.a.run.app/docs)** - Interactive Swagger UI

---

## 🎯 For Evaluators

### Quick Verification (5 minutes)

1. **Test Live API:**
   ```
   curl https://kasparro-api-nk6gux63sq-el.a.run.app/api/v1/health
   ```

2. **View Cloud Scheduler (Cron Jobs):**
   https://console.cloud.google.com/cloudscheduler?project=forward-logic-482607-k3

3. **View Cloud Logs:**
   https://console.cloud.google.com/run/detail/asia-south1/kasparro-api/logs?project=forward-logic-482607-k3

4. **Run Local Smoke Test:**
   ```
   git clone https://github.com/pruthvir7/kasparro-backend-pruthvi-r.git
   cd kasparro-backend-pruthvi-r
   docker-compose up --build  # Wait 90 seconds
   ./smoke_test.sh            # 14 tests pass
   ```

### Requirements Checklist

| Requirement | Status | Evidence |
|-------------|--------|----------|
| API Authentication | ✅ | X-API-Key on all data endpoints |
| Docker Auto-ETL | ✅ | ETL runs on container startup |
| Cloud Deployment | ✅ | GCP Cloud Run + Cloud Scheduler |
| Automated Tests | ✅ | 17 pytest + 14 smoke tests |
| Smoke Test Script | ✅ | `./smoke_test.sh` passes |
| Documentation | ✅ | README + DEPLOYMENT + CLOUD_DEPLOYMENT |

---

## 💰 Cost Estimation

**GCP Monthly Costs:**
- Cloud Run: $0-5 (free tier: 2M requests/month)
- Cloud SQL: $7-10 (db-f1-micro)
- Cloud Scheduler: $0.10
- Cloud Logging: $0 (50GB/month free)

**Total: ~$8-15/month**

---

## 🤝 Support

**Repository:** https://github.com/pruthvir7/kasparro-backend-pruthvi-r  
**Live API:** https://kasparro-api-nk6gux63sq-el.a.run.app  
**Documentation:** https://kasparro-api-nk6gux63sq-el.a.run.app/docs

---

**Made with ❤️ for Kasparro**
