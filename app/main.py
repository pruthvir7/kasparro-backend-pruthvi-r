from fastapi import FastAPI, Request
from app.api.endpoints import router
from app.core.database import engine, Base
from contextlib import asynccontextmanager
from app.utils.metrics import api_requests_total, api_request_duration
from app.utils.rate_limiter import rate_limiter
from fastapi.responses import JSONResponse
import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title="Kasparro Crypto API",
    description="Production-grade ETL and API for cryptocurrency data",
    version="1.0.0",
    lifespan=lifespan
)

# Rate limiting middleware (FIRST - before metrics)
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for metrics endpoint and health check
    if request.url.path in ["/api/v1/metrics", "/api/v1/health", "/"]:
        return await call_next(request)
    
    # Use IP address as identifier
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        await rate_limiter.check_rate_limit(client_ip)
    except Exception as e:
        # If it's an HTTPException with rate limit error
        if hasattr(e, 'status_code') and e.status_code == 429:
            return JSONResponse(
                status_code=429,
                content=e.detail,
                headers={"Retry-After": "60"}
            )
        raise
    
    return await call_next(request)

# Metrics middleware (SECOND - after rate limiting)
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # Track metrics
    api_requests_total.labels(
        endpoint=request.url.path,
        method=request.method,
        status=response.status_code
    ).inc()
    
    api_request_duration.labels(
        endpoint=request.url.path,
        method=request.method
    ).observe(duration)
    
    return response

app.include_router(router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Kasparro Crypto API", "docs": "/docs"}
