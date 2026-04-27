from datetime import datetime

from fastapi import APIRouter

from app.config import settings
from app.services.data_service import data_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Проверка состояния API"""
    available_years = data_service.get_available_years()

    # Проверяем доступность Ollama.
    ollama_available = False
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.OLLAMA_HOST}/api/tags")
            ollama_available = response.status_code == 200
    except Exception:
        pass

    return {
        "status": "healthy" if available_years else "degraded",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "years_available": available_years,
            "total_records": sum(
                len(data_frame) if data_frame is not None else 0
                for data_frame in (data_service.loader.load_year(year) for year in available_years[:3])
            ),
        },
        "llama": {
            "available": ollama_available,
            "host": settings.OLLAMA_HOST,
            "default_model": settings.DEFAULT_MODEL,
        },
    }


@router.get("/ready")
async def readiness_check():
    """Проверка готовности API к работе"""
    available_years = data_service.get_available_years()
    is_ready = len(available_years) > 0

    return {
        "ready": is_ready,
        "message": "API is ready" if is_ready else "No data loaded",
        "years_loaded": available_years,
    }
