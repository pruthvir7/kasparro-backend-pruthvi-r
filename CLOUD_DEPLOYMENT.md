# GCP Cloud Deployment Documentation

## Deployed Services

### 1. Cloud Run API
**Service URL:** https://kasparro-api-545961211138.asia-south1.run.app

**Endpoints:**
- Health: `GET /api/v1/health`
- Data: `GET /api/v1/data?limit=10` (requires `X-API-Key` header)
- Stats: `GET /api/v1/stats` (requires `X-API-Key` header)
- Manual ETL: `POST /api/v1/etl/run` (requires `X-API-Key` header)
- Metrics: `GET /api/v1/metrics`
- Docs: `GET /docs`

**API Key:** `kasparro_secret_key_2025`

### 2. Cloud SQL PostgreSQL
**Instance:** `kasparro-db`
**Region:** `asia-south1` (Mumbai)
**Database:** `kasparro`
**Connection:** `forward-logic-482607-k3:asia-south1:kasparro-db`

### 3. Cloud Scheduler (Cron Jobs)
**Job Name:** `kasparro-etl-hourly`
**Schedule:** Every hour (`0 * * * *`)
**Timezone:** UTC
**Action:** Triggers ETL pipeline via POST to `/api/v1/etl/run`

---

## Access GCP Dashboards (For Evaluation)

### Cloud Scheduler (View Cron Jobs)
```
https://console.cloud.google.com/cloudscheduler?project=forward-logic-482607-k3
```

### Cloud Run Logs
```
https://console.cloud.google.com/run/detail/asia-south1/kasparro-api/logs?project=forward-logic-482607-k3
```

### Cloud Logging (All Logs)
```
https://console.cloud.google.com/logs/query?project=forward-logic-482607-k3
```

### Cloud SQL Instance
```
https://console.cloud.google.com/sql/instances/kasparro-db/overview?project=forward-logic-482607-k3
```

---

## Testing Commands

### Test API Health
```
curl https://kasparro-api-545961211138.asia-south1.run.app/api/v1/health
```

### Test Data Endpoint (with API Key)
```
curl -H "X-API-Key: kasparro_secret_key_2025" \
  "https://kasparro-api-545961211138.asia-south1.run.app/api/v1/data?limit=5"
```

### Test Statistics
```
curl -H "X-API-Key: kasparro_secret_key_2025" \
  "https://kasparro-api-545961211138.asia-south1.run.app/api/v1/stats"
```

### Manually Trigger ETL
```
curl -X POST -H "X-API-Key: kasparro_secret_key_2025" \
  "https://kasparro-api-545961211138.asia-south1.run.app/api/v1/etl/run"
```

### Manually Trigger Cron Job
```
gcloud scheduler jobs run kasparro-etl-hourly --location=asia-south1
```

---

## Viewing Logs

### Cloud Run Logs (CLI)
```
gcloud run services logs read kasparro-api --region=asia-south1 --limit=50
```

### Cloud Scheduler Logs (CLI)
```
gcloud scheduler jobs describe kasparro-etl-hourly --location=asia-south1
```

### Filter Logs for ETL Events
```
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=kasparro-api AND textPayload=~'ETL'" --limit=50 --format=json
```

---

## Monitoring & Metrics

### Prometheus Metrics Endpoint
```
https://kasparro-api-545961211138.asia-south1.run.app/api/v1/metrics
```

### Key Metrics:
- `api_requests_total` - Total API requests
- `api_request_duration_seconds` - Request latency
- `etl_runs_total` - Total ETL executions
- `etl_records_processed_total` - Total records processed

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Google Cloud Platform                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐         ┌──────────────────┐          │
│  │ Cloud Scheduler │────────▶│   Cloud Run      │          │
│  │  (Hourly Cron)  │  POST   │  (FastAPI App)   │          │
│  │  0 * * * *      │         │  Port: 8080      │          │
│  └─────────────────┘         └────────┬─────────┘          │
│                                        │                     │
│                                        │ Unix Socket         │
│                                        │                     │
│                               ┌────────▼─────────┐          │
│                               │   Cloud SQL      │          │
│                               │  (PostgreSQL 15) │          │
│                               │  Database: kasparro          │
│                               └──────────────────┘          │
│                                                               │
│  ┌─────────────────┐         ┌──────────────────┐          │
│  │ Cloud Logging   │         │ Cloud Monitoring │          │
│  │ (Logs Storage)  │         │ (Metrics)        │          │
│  └─────────────────┘         └──────────────────┘          │
│                                                               │
└─────────────────────────────────────────────────────────────┘

External Data Sources:
  ┌─────────────┐    ┌─────────────┐
  │  CoinGecko  │    │ CoinPaprika │
  │     API     │    │     API     │
  └─────────────┘    └─────────────┘
```

---

## Deployment Process

### Initial Setup

1. **Enable Required APIs:**
   ```
   gcloud services enable run.googleapis.com \
     sqladmin.googleapis.com \
     cloudscheduler.googleapis.com \
     cloudbuild.googleapis.com \
     artifactregistry.googleapis.com
   ```

2. **Create Cloud SQL Instance:**
   ```
   gcloud sql instances create kasparro-db \
     --database-version=POSTGRES_15 \
     --tier=db-f1-micro \
     --region=asia-south1 \
     --root-password=YOUR_PASSWORD
   ```

3. **Create Database:**
   ```
   gcloud sql databases create kasparro --instance=kasparro-db
   ```

4. **Deploy to Cloud Run:**
   ```
   gcloud run deploy kasparro-api \
     --source . \
     --region=asia-south1 \
     --platform=managed \
     --allow-unauthenticated \
     --env-vars-file=env.yaml \
     --add-cloudsql-instances=CONNECTION_NAME \
     --memory=512Mi \
     --cpu=1 \
     --timeout=300
   ```

5. **Set Up Cloud Scheduler:**
   ```
   # Create service account
   gcloud iam service-accounts create cloud-scheduler-sa
   
   # Grant permissions
   gcloud run services add-iam-policy-binding kasparro-api \
     --region=asia-south1 \
     --member="serviceAccount:cloud-scheduler-sa@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.invoker"
   
   # Create cron job
   gcloud scheduler jobs create http kasparro-etl-hourly \
     --location=asia-south1 \
     --schedule="0 * * * *" \
     --uri="https://kasparro-api-545961211138.asia-south1.run.app/api/v1/etl/run" \
     --http-method=POST \
     --headers="X-API-Key=kasparro_secret_key_2025" \
     --oidc-service-account-email="cloud-scheduler-sa@PROJECT_ID.iam.gserviceaccount.com" \
     --oidc-token-audience="https://kasparro-api-545961211138.asia-south1.run.app"
   ```

---

## Security

- ✅ API Key authentication on all data endpoints
- ✅ Cloud SQL accessible only via Cloud Run (Unix socket)
- ✅ Service account with minimal permissions (Cloud Run Invoker only)
- ✅ HTTPS only (enforced by Cloud Run)
- ✅ No public database access
- ✅ Environment variables stored securely in Cloud Run config

---

## Cost Estimation

**Monthly Cost (Approximate):**
- **Cloud Run:** $0-5 (within free tier: 2M requests/month, 360K GB-seconds)
- **Cloud SQL (db-f1-micro):** $7-10/month
- **Cloud Scheduler:** $0.10/job/month
- **Cloud Logging:** Free (50GB/month free tier)
- **Cloud Build:** $0 (120 build-minutes/day free)

**Total: ~$8-15/month**

**Free Tier Details:**
- Cloud Run: First 2M requests/month free
- Cloud Scheduler: First 3 jobs free
- Cloud Logging: 50GB/month free
- Cloud Build: 120 build-minutes/day free

---

## Troubleshooting

### Check Service Status
```
gcloud run services describe kasparro-api --region=asia-south1
```

### View Recent Logs
```
gcloud run services logs read kasparro-api --region=asia-south1 --limit=100
```

### Test Database Connection
```
gcloud sql connect kasparro-db --user=postgres --quiet
```

### Verify Cron Job
```
gcloud scheduler jobs describe kasparro-etl-hourly --location=asia-south1
```

### Manual ETL Trigger
```
curl -X POST -H "X-API-Key: kasparro_secret_key_2025" \
  "https://kasparro-api-545961211138.asia-south1.run.app/api/v1/etl/run"
```

---

## Environment Variables

### Required Environment Variables:
- `DATABASE_URL`: PostgreSQL connection string (Cloud SQL Unix socket)
- `API_KEY`: API authentication key
- `COINGECKO_API_KEY`: CoinGecko API key
- `ENVIRONMENT`: Deployment environment (production/development)

### Set in Cloud Run:
```
gcloud run services update kasparro-api \
  --region=asia-south1 \
  --set-env-vars="KEY=VALUE"
```

---

## Maintenance

### Update Deployment
```
gcloud run deploy kasparro-api --source . --region=asia-south1
```

### Scale Service
```
gcloud run services update kasparro-api \
  --region=asia-south1 \
  --min-instances=0 \
  --max-instances=10
```

### Update Cron Schedule
```
gcloud scheduler jobs update http kasparro-etl-hourly \
  --location=asia-south1 \
  --schedule="0 */2 * * *"  # Every 2 hours
```

### Backup Database
```
gcloud sql backups create --instance=kasparro-db
```

---

## Support & Documentation

**Project ID:** `forward-logic-482607-k3`  
**Region:** `asia-south1` (Mumbai, India)  
**Deployed:** December 28, 2025  

**Related Documentation:**
- [README.md](README.md) - Project overview
- [DEPLOYMENT.md](DEPLOYMENT.md) - Local deployment guide
- [API Documentation](https://kasparro-api-545961211138.asia-south1.run.app/docs) - Interactive API docs

**GCP Console:**
- [Project Dashboard](https://console.cloud.google.com/home/dashboard?project=forward-logic-482607-k3)
- [Cloud Run](https://console.cloud.google.com/run?project=forward-logic-482607-k3)
- [Cloud SQL](https://console.cloud.google.com/sql?project=forward-logic-482607-k3)
- [Cloud Scheduler](https://console.cloud.google.com/cloudscheduler?project=forward-logic-482607-k3)
