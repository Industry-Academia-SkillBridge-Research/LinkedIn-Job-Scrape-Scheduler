"""
Configuration settings for the API
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # API Info
    APP_NAME: str = "LinkedIn Job Scraper API"
    APP_VERSION: str = "2.0.0"
    APP_DESCRIPTION: str = "REST API for scraping LinkedIn job listings with automated scheduling and Elasticsearch integration"
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    # Scraper Settings
    DEFAULT_MAX_JOBS: int = 10
    DEFAULT_DELAY_MIN: float = 2.0
    DEFAULT_DELAY_MAX: float = 4.0
    DEFAULT_FETCH_DETAILS: bool = True
    
    # Rate Limiting
    MAX_JOBS_PER_REQUEST: int = 50
    
    # Output Directory
    OUTPUT_DIR: str = "output"
    
    # Elasticsearch Configuration
    ELASTICSEARCH_ENABLED: bool = True
    ELASTICSEARCH_HOST: str = "localhost"
    ELASTICSEARCH_PORT: int = 9200
    ELASTICSEARCH_SCHEME: str = "http"
    ELASTICSEARCH_USER: Optional[str] = None
    ELASTICSEARCH_PASSWORD: Optional[str] = None
    ELASTICSEARCH_INDEX: str = "linkedin_jobs"
    
    # Scheduler Configuration
    AUTO_START_SCHEDULER: bool = False
    SCHEDULER_DAY: str = "monday"
    SCHEDULER_TIME: str = "09:00"
    
    # Job Quality Settings
    MAX_POST_AGE_DAYS: int = 21
    JOBS_PER_ROLE: int = 20
    EXACT_MATCH: bool = True
    
    # Location Priority
    PRIMARY_LOCATION: str = "Sri Lanka"
    PRIMARY_COUNTRY_CODE: str = "LK"
    FALLBACK_LOCATIONS: str = "United States,India,United Kingdom"
    FALLBACK_COUNTRY_CODES: str = "US,IN,GB"
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from .env file


settings = Settings()
