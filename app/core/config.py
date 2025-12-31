import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    COINGECKO_API_KEY: str = "not_required_for_free_tier"
    API_KEY: str = "kasparro_secret_key_2025"  # Default for testing
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
