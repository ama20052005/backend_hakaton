# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.config import settings
from app.api.routes import health, data, analysis
from app.services.data_service import data_service

# Настройка логирования
logger.remove()
logger.add(sys.stdout, level=settings.LOG_LEVEL)
logger.add("logs/api.log", rotation="1 day", level="INFO")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    logger.info(f"Data directory: {settings.DATA_DIR}")
    
    available_years = data_service.get_available_years()
    logger.info(f"Available years: {available_years}")
    
    if not available_years:
        logger.warning("No data files found! Please add CSV files to data/yearly/ directory")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")

# Создание приложения
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API для анализа демографических данных России с интеграцией LLaMA",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация роутеров
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(data.router, prefix=settings.API_V1_PREFIX)
app.include_router(analysis.router, prefix=settings.API_V1_PREFIX)

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "api_prefix": settings.API_V1_PREFIX
    }