from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    COINGECKO_API_KEY: str
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
