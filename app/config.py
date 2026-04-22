from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Demography Analysis API"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # LLaMA (Ollama) settings
    OLLAMA_HOST: str = "http://localhost:11434"
    DEFAULT_MODEL: str = "llama3.2:3b"
    LLAMA_TIMEOUT: int = 120
    LLAMA_TEMPERATURE: float = 0.7
    LLAMA_MAX_TOKENS: int = 1000
    
    # Data settings
    DATA_DIR: str = "data/yearly"
    CSV_ENCODING: str = "utf-8-sig"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
