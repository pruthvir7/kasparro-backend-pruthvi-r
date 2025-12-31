# GCP Cloud Deployment Documentation


**🚀 PRODUCTION STATUS:** ✅ LIVE | 115 coins | 81 multi-source | Scheduler=kasparro-etl-15min (ENABLED)


## 🌐 Deployed Services


### 1. Cloud Run API
**Service URL:** https://kasparro-api-545961211138.asia-south1.run.app


**🔥 LIVE Test Commands (Copy-Paste):**
```bash
# Load test credentials
source .env.test

# Health + ETL status
curl https://kasparro-api-545961211138.asia-south1.run.app/api/v1/health


# BTC Normalization (2 sources → 1 coin) 
curl -H "X-API-Key: ${API_KEY}" \
  "https://kasparro-api-545961211138.asia-south1.run.app/api/v1/coins?limit=200" \
  | jq '.coins[] | select(.symbol=="BTC") | {symbol, source_count: (.source_identifiers | length)}'


# Live Stats (1212 records, 3 sources)
curl -H "X-API-Key: ${API_KEY}" \
  "https://kasparro-api-545961211138.asia-south1.run.app/api/v1/stats"
```


**Endpoints:**
| Endpoint | Auth | Purpose | Live Example |
|----------|------|---------|--------------|
| `GET /api/v1/health` | No | System + ETL status | [Try](https://kasparro-api-545961211138.asia-south1.run.app/api/v1/health) |
| `GET /api/v1/stats` | Yes | Records by source | `1212 total, 3 sources` |
| `GET /api/v1/data` | Yes | Price data | `?coin=BTC&limit=5` |
| **`GET /api/v1/coins`** | Yes | **Normalization** | `115 coins, 81 multi-source` |
| `POST /api/v1/etl/run` | Yes | Manual ETL | Triggers 3 sources |
| `GET /api/v1/metrics` | No | Prometheus | Monitoring |


**API Key:** See `.env.test` for test credentials


### 2. Cloud SQL PostgreSQL
**Instance:** `kasparro-db`
**Region:** `asia-south1` (Mumbai)
**Database:** `kasparro`
**Connection:** `forward-logic-482607-k3:asia-south1:kasparro-db`
**Live Data:** 115 coins | 202 identifiers | 1212 price records


### 3. Cloud Scheduler ✅ **UPDATED**
**Job Name:** `kasparro-etl-15min`
**Schedule:** `*/15 * * * *` (every **15 minutes**)
**Timezone:** Asia/Kolkata
**Target:** `POST https://kasparro-api-545961211138.asia-south1.run.app/api/v1/etl/run`
**Status:** `ENABLED`


**Verify Live:**
```bash
gcloud scheduler jobs list --location=asia-south1
```


---


## 🔗 GCP Dashboards (Evaluator Access)


| Service | Console Link | Status |
|---------|--------------|--------|
| [Cloud Scheduler](https://console.cloud.google.com/cloudscheduler?project=forward-logic-482607-k3) | `kasparro-etl-15min` | ✅ ENABLED |
| [Cloud Run Logs](https://console.cloud.google.com/run/detail/asia-south1/kasparro-api/logs?project=forward-logic-482607-k3) | Recent ETL | ✅ Live |
| [Cloud SQL](https://console.cloud.google.com/sql/instances/kasparro-db/overview?project=forward-logic-482607-k3) | 1212 records | ✅ Healthy |
| [API Docs](https://kasparro-api-545961211138.asia-south1.run.app/docs) | Swagger UI | ✅ Interactive |
| [Project Dashboard](https://console.cloud.google.com/home/dashboard?project=forward-logic-482607-k3) | Overview | ✅ All green |


---


## 🧪 Production Verification (30 seconds)


```bash
# Load credentials
source .env.test

# 1. Health Check
curl https://kasparro-api-545961211138.asia-south1.run.app/api/v1/health | jq .status


# 2. Live Stats
curl -H "X-API-Key: ${API_KEY}" \
  "https://kasparro-api-545961211138.asia-south1.run.app/api/v1/stats" | jq '{total_records, total_sources, records_by_source}'


# 3. Normalization Proof (BTC)
curl -H "X-API-Key: ${API_KEY}" \
  "https://kasparro-api-545961211138.asia-south1.run.app/api/v1/coins?limit=200" \
  | jq '.total_count, (.coins[] | select(.symbol=="BTC") | {symbol, source_count: (.source_identifiers | length)})'


# 4. Manual ETL Trigger
curl -X POST -H "X-API-Key: ${API_KEY}" \
  "https://kasparro-api-545961211138.asia-south1.run.app/api/v1/etl/run"


# 5. Scheduler Status
gcloud scheduler jobs list --location=asia-south1 --format="table[no-heading](name.basename(),state,schedule)"
```


**Expected Output:**
```
"healthy"
115
{"coingecko": 2, "coinpaprika": 2}
kasparro-etl-15min  ENABLED  */15 * * * *
```


---


## 🏗️ Production Architecture


```
┌────────────────────┐     */15 * * * *     ┌──────────────────┐
│ Cloud Scheduler    │ ───────────────────▶ │ Cloud Run API    │
│ kasparro-etl-15min │                       │ FastAPI v1.0     │
│ (Asia/Kolkata)     │                       │ 115 coins loaded │
└────────────────────┘                       └────────┬─────────┘
                                                     │
                                        Unix Socket  │
                                                     │
                                              ┌──────▼──────┐
                                              │ Cloud SQL   │ ← 1212 records
                                              │ kasparro-db │
                                              │ PostgreSQL15│
                                              └──────────────┘
```


**Data Flow:** `CoinGecko → CoinPaprika → CSV → Normalized Schema (81 multi-source coins)`


## 🔧 Maintenance Commands


```bash
# View logs (last 100)
gcloud run services logs read kasparro-api --region=asia-south1 --limit=100


# Trigger ETL immediately
curl -X POST -H "X-API-Key: ${API_KEY}" \
  "https://kasparro-api-545961211138.asia-south1.run.app/api/v1/etl/run"


# Run scheduler manually
gcloud scheduler jobs run kasparro-etl-15min --location=asia-south1


# Scale (0-10 instances)
gcloud run services update kasparro-api --region=asia-south1 --max-instances=10


# Check service status
gcloud run services describe kasparro-api --region=asia-south1
```


---


## 💰 Cost Breakdown (~$8-15/month)


| Service | Cost | Free Tier |
|---------|------|-----------|
| **Cloud Run** | $0-5 | 2M requests/month |
| **Cloud SQL** | $7-10 | db-f1-micro |
| **Scheduler** | $0.10 | 3 jobs free |
| **Logging** | $0 | 50GB/month |


---


## ✅ Production Checklist


| Item | Status | Verification |
|------|--------|--------------|
| ✅ **API Live** | https://kasparro-api-... | `curl /health` |
| ✅ **115 Coins** | 81 multi-source | `/coins?limit=200` |
| ✅ **Scheduler** | kasparro-etl-15min | `gcloud scheduler list` |
| ✅ **Database** | 1212 records | `/stats` |
| ✅ **Normalization** | BTC=2 sources | `/coins?symbol=BTC` |
| ✅ **Auto-ETL** | Every 15min | `kasparro-etl-15min` |


---


## 🔐 Security


- ✅ **API Key** auth (all data endpoints)
- ✅ **Cloud SQL** Unix socket only (no public access)
- ✅ **HTTPS** enforced (Cloud Run)
- ✅ **Rate limiting** (100 req/min/IP)
- ✅ **Minimal IAM** (Cloud Run Invoker only)
- ✅ **Secrets** in environment variables


---


**Project:** `forward-logic-482607-k3` | **Region:** `asia-south1` | **Deployed:** Dec 29, 2025  
**LIVE & PRODUCTION READY!** 🚀
