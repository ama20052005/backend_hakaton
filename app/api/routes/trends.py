from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional, List

from app.services.trends_service import trends_service
from app.services.data_service import data_service

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/growth-decline")
async def get_growth_decline(
    start_year: int = Query(2012, ge=2012, le=2024, description="Начальный год"),
    end_year: int = Query(2024, ge=2012, le=2024, description="Конечный год"),
    limit: int = Query(10, ge=1, le=50, description="Количество записей")
):
    """
    Таблица муниципалитетов с наибольшим ростом и снижением населения.
    
    Возвращает:
    - Лидеры роста (топ N)
    - Лидеры снижения (топ N)
    - Абсолютное и процентное изменение для каждого
    """
    if start_year > end_year:
        raise HTTPException(status_code=400, detail="start_year must be <= end_year")
    
    result = trends_service.get_growth_decline(
        start_year=start_year,
        end_year=end_year,
        limit=limit
    )
    
    return {
        "success": True,
        "period": {
            "start_year": start_year,
            "end_year": end_year,
            "years_span": end_year - start_year
        },
        "growth_leaders": result.growth,
        "decline_leaders": result.decline,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/population-change")
async def get_population_change(
    start_year: int = Query(2012, ge=2012, le=2024, description="Начальный год"),
    end_year: int = Query(2024, ge=2012, le=2024, description="Конечный год"),
    region_code: Optional[str] = Query(None, description="Код региона (опционально)"),
    region_name: Optional[str] = Query(None, description="Название региона (опционально)")
):
    """
    Рассчитывает динамику изменения населения за выбранный период.
    """
    if start_year > end_year:
        raise HTTPException(status_code=400, detail="start_year must be <= end_year")
    
    # Получаем данные за начальный и конечный год
    if region_code or region_name:
        if region_code:
            start_data = data_service.get_municipality(region_code, start_year)
            end_data = data_service.get_municipality(region_code, end_year)
            if not start_data or not end_data:
                raise HTTPException(status_code=404, detail=f"Регион с кодом {region_code} не найден")
            name = start_data['name']
        else:
            results = data_service.search_municipality(region_name, end_year, limit=1)
            if not results:
                raise HTTPException(status_code=404, detail=f"Регион '{region_name}' не найден")
            code = results[0]['code']
            start_data = data_service.get_municipality(code, start_year)
            end_data = results[0]
            if not start_data:
                raise HTTPException(status_code=404, detail=f"Нет данных за {start_year} год для региона '{region_name}'")
            name = results[0]['name']
    else:
        start_data = data_service.get_year_statistics(start_year)
        end_data = data_service.get_year_statistics(end_year)
        name = "Россия"
    
    if not start_data or not end_data:
        raise HTTPException(status_code=404, detail=f"Нет данных за {start_year} или {end_year} год")
    
    start_pop = start_data['total_population']
    end_pop = end_data['total_population']
    
    absolute_change = end_pop - start_pop
    percent_change = (absolute_change / start_pop) * 100 if start_pop > 0 else 0
    
    years_diff = end_year - start_year
    if years_diff > 0 and start_pop > 0:
        cagr = ((end_pop / start_pop) ** (1 / years_diff) - 1) * 100
    else:
        cagr = 0
    
    if percent_change > 0:
        trend_type = "рост"
        trend_icon = "📈"
    elif percent_change < 0:
        trend_type = "снижение"
        trend_icon = "📉"
    else:
        trend_type = "стабильность"
        trend_icon = "➡️"
    
    return {
        "success": True,
        "region": name,
        "period": {
            "start_year": start_year,
            "end_year": end_year,
            "years_span": years_diff
        },
        "population": {
            "start": start_pop,
            "end": end_pop,
            "start_formatted": f"{start_pop:,}",
            "end_formatted": f"{end_pop:,}"
        },
        "change": {
            "absolute": absolute_change,
            "absolute_formatted": f"{absolute_change:+,}",
            "percent": round(percent_change, 2),
            "percent_formatted": f"{percent_change:+.2f}%",
            "trend_type": trend_type,
            "trend_icon": trend_icon
        },
        "annual_growth": {
            "cagr_percent": round(cagr, 2),
            "cagr_formatted": f"{cagr:+.2f}%",
            "average_annual_change": round(absolute_change / years_diff, 0) if years_diff > 0 else 0
        },
        "timestamp": datetime.now().isoformat()
    }
