from typing import List, Optional, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-professional-secret-key-for-local-dev"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    PROJECT_NAME: str = "TrustScope B2B"
    
    # PostgreSQL database connection string
    SQLALCHEMY_DATABASE_URI: str = "postgresql://postgres:postgres@db:5432/trustscope"

    class Config:
        case_sensitive = True

settings = Settings()
