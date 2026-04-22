from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.config import settings
from app.api.routes import health_router, data_router, analysis_router
from app.services.data_service import data_service

# Настройка логирования
logger.remove()
logger.add(sys.stdout, level=settings.LOG_LEVEL)
logger.add("logs/api.log", rotation="1 day", level="INFO")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    logger.info(f"Data directory: {settings.DATA_DIR}")
    
    available_years = data_service.get_available_years()
    logger.info(f"Available years: {available_years}")
    
    if not available_years:
        logger.warning("No data files found! Please add CSV files to data/yearly/ directory")
    
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API для анализа демографических данных России с интеграцией LLaMA",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация роутеров (health_router уже сам роутер, не нужно .router)
app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(data_router, prefix=settings.API_V1_PREFIX)
app.include_router(analysis_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "api_prefix": settings.API_V1_PREFIX
    }
