from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY

# API metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['endpoint', 'method']
)

# ETL metrics
etl_runs_total = Counter(
    'etl_runs_total',
    'Total ETL runs',
    ['source', 'status']
)

etl_duration_seconds = Histogram(
    'etl_duration_seconds',
    'ETL execution duration',
    ['source']
)

etl_records_processed = Counter(
    'etl_records_processed_total',
    'Total records processed',
    ['source']
)

# Database metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

crypto_records_total = Gauge(
    'crypto_records_total',
    'Total cryptocurrency records in database'
)

# Rate limiting metrics
rate_limit_exceeded_total = Counter(
    'rate_limit_exceeded_total',
    'Total rate limit exceeded events',
    ['identifier']
)
