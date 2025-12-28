import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    COINGECKO_API_KEY: str
    API_KEY: str = os.getenv("API_KEY", "your-secret-api-key-here")
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"

settings = Settings()
