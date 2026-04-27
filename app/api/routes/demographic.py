from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime

from app.services.demographic_service import demographic_service

router = APIRouter(prefix="/demographic", tags=["demographic"])


@router.get("/indicators/{year}")
async def get_demographic_indicators(year: int):
    """
    Получить демографические показатели за год:
    - Рождаемость (количество и коэффициент на 1000 человек)
    - Смертность (количество и коэффициент на 1000 человек)
    - Естественный прирост (количество и коэффициент на 1000 человек)
    - Миграция (прибывшие, выбывшие, миграционный прирост)
    """
    available_years = demographic_service.get_available_years()
    
    if year not in available_years:
        return {
            "success": False,
            "error": f"Нет данных за {year} год",
            "available_years": available_years[:20]
        }
    
    result = demographic_service.get_demographic_indicators(year)
    
    return {
        "success": True,
        "data": result,
        "timestamp": datetime.now().isoformat()
    }