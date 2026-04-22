from fastapi import APIRouter
from datetime import datetime
from app.services.data_service import data_service

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check():
    available_years = data_service.get_available_years()
    
    # Подсчет общего количества записей
    total_records = 0
    for year in available_years[:3]:  # берем первые 3 года для скорости
        df = data_service.loader.load_year(year)
        if df is not None:
            total_records += len(df)
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "years_available": available_years,
            "total_records": total_records
        }
    }

@router.get("/ready")
async def readiness_check():
    available_years = data_service.get_available_years()
    is_ready = len(available_years) > 0
    
    return {
        "ready": is_ready,
        "message": "API is ready" if is_ready else "No data loaded",
        "years_loaded": available_years
    }
