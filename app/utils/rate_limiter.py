from fastapi import HTTPException
from datetime import datetime, timedelta
from collections import defaultdict
import structlog

logger = structlog.get_logger()


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    async def check_rate_limit(self, identifier: str):
        """Check if request exceeds rate limit"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old requests (remove requests older than 1 minute)
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > minute_ago
        ]
        
        # Check if limit exceeded
        current_count = len(self.requests[identifier])
        
        if current_count >= self.requests_per_minute:
            # Import here to avoid circular dependency
            from app.utils.metrics import rate_limit_exceeded_total
            
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                requests=current_count,
                limit=self.requests_per_minute
            )
            
            # Track in metrics
            rate_limit_exceeded_total.labels(identifier=identifier).inc()
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute allowed",
                    "retry_after": 60
                }
            )
        
        # Record this request
        self.requests[identifier].append(now)
        
        logger.debug(
            "rate_limit_check",
            identifier=identifier,
            requests=current_count + 1,
            limit=self.requests_per_minute
        )


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=100)
