# app/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # API settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Demography Analysis API with LLaMA"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # LLaMA (Ollama) settings
    OLLAMA_HOST: str = "http://localhost:11434"
    DEFAULT_MODEL: str = "llama3.2:3b"
    AVAILABLE_MODELS: List[str] = ["llama3.2:3b", "llama3.1:8b", "mistral:7b"]
    LLAMA_TIMEOUT: int = 120
    LLAMA_TEMPERATURE: float = 0.7
    LLAMA_MAX_TOKENS: int = 1000
    
    # CSV Data settings - поддержка нескольких лет
    DATA_DIR: str = "data/yearly"
    YEARS: List[int] = list(range(2012, 2025))  # 2012-2024
    CSV_ENCODING: str = "utf-8-sig"

    # Reports
    REPORTS_DIR: str = "generated_reports"
    
    # Cache settings
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600  # 1 hour
    REDIS_URL: Optional[str] = None
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_PERIOD: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
