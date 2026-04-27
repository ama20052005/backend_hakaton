from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional

from app.services.forecast_service import forecast_service
from app.services.llama_service import llama_service

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.post("/ai-forecast")
async def ai_forecast(
    region_name: str = Query("Россия", description="Название региона"),
    years_ahead: int = Query(10, ge=5, le=15, description="Горизонт прогноза (5-15 лет)"),
    model: Optional[str] = Query(None, description="Модель LLaMA (например, llama3.2:3b)")
):
    """
    🧠 ИИ-ПРОГНОЗ с использованием LLaMA
    
    LLaMA анализирует исторические данные и делает прогноз:
    - Анализирует тренды за прошлые годы
    - Учитывает демографические факторы
    - Предоставляет обоснование прогноза
    - Дает рекомендации по социальной политике
    - Рассчитывает доверительные интервалы
    """
    # Получаем исторические данные
    if region_name.lower() == "россия":
        historical_data = forecast_service.get_russia_history()
    else:
        historical_data = forecast_service.get_region_history(region_name)
    
    # Проверяем наличие данных
    if not historical_data or len(historical_data) < 3:
        raise HTTPException(
            status_code=404,
            detail=f"Недостаточно исторических данных для {region_name}. Нужно минимум 3 года."
        )
    
    # Генерируем ИИ-прогноз
    forecast_result = await llama_service.generate_forecast(
        historical_data=historical_data,
        years_ahead=years_ahead,
        region_name=region_name,
        model=model
    )
    
    # Добавляем метаданные
    forecast_result['historical_data'] = [
        {"year": item['year'], "value": item['value']}
        for item in historical_data
    ]
    forecast_result['region'] = region_name
    forecast_result['forecast_horizon_years'] = years_ahead
    
    return forecast_result
