from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models import GrowthDeclineResponse
from app.services.data_service import data_service
from app.services.trends_service import trends_service

router = APIRouter(prefix="/trends", tags=["trends"])


def _field(record, name: str):
    if record is None:
        return None
    if isinstance(record, dict):
        return record.get(name)
    return getattr(record, name, None)


@router.get("/growth-decline", response_model=GrowthDeclineResponse)
async def get_growth_decline(
    start_year: int = Query(2012, ge=2012, le=2024),
    end_year: int = Query(2024, ge=2012, le=2024),
    limit: int = Query(10, ge=1, le=50),
):
    """Возвращает лидеров роста и снижения по населению за период."""

    if start_year > end_year:
        raise HTTPException(status_code=400, detail="start_year must be <= end_year")

    return trends_service.get_growth_decline(
        start_year=start_year,
        end_year=end_year,
        limit=limit,
    )


@router.get("/population-change")
async def get_population_change(
    start_year: int = Query(2012, ge=2012, le=2024, description="Начальный год"),
    end_year: int = Query(2024, ge=2012, le=2024, description="Конечный год"),
    region_code: Optional[str] = Query(None, description="Код региона"),
    region_name: Optional[str] = Query(None, description="Название региона"),
):
    """Возвращает изменение численности населения за выбранный период."""

    if start_year > end_year:
        raise HTTPException(status_code=400, detail="start_year must be <= end_year")

    if region_code:
        start_data = data_service.get_municipality(region_code, start_year)
        end_data = data_service.get_municipality(region_code, end_year)
        if not start_data or not end_data:
            raise HTTPException(status_code=404, detail=f"Region with code {region_code} not found")
        region_label = _field(start_data, "name")
    elif region_name:
        start_data = data_service.get_region_by_name(region_name, start_year)
        end_data = data_service.get_region_by_name(region_name, end_year)

        if not start_data or not end_data:
            matches = data_service.search_municipality(region_name, end_year, limit=1)
            if not matches:
                raise HTTPException(status_code=404, detail=f"Region '{region_name}' not found")

            matched_code = _field(matches[0], "code")
            start_data = data_service.get_municipality(matched_code, start_year)
            end_data = data_service.get_municipality(matched_code, end_year)
            if not start_data or not end_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Region '{region_name}' does not have data for both years",
                )

        region_label = _field(end_data, "name")
    else:
        start_data = data_service.get_year_statistics(start_year)
        end_data = data_service.get_year_statistics(end_year)
        region_label = "Россия"

    if not start_data or not end_data:
        raise HTTPException(
            status_code=404,
            detail=f"No data for {start_year} or {end_year}",
        )

    start_population = _field(start_data, "total_population")
    end_population = _field(end_data, "total_population")
    absolute_change = end_population - start_population
    percent_change = (absolute_change / start_population) * 100 if start_population > 0 else 0

    year_span = end_year - start_year
    annual_growth_rate = 0.0
    if year_span > 0 and start_population > 0:
        annual_growth_rate = ((end_population / start_population) ** (1 / year_span) - 1) * 100

    if percent_change > 0:
        trend_type = "рост"
    elif percent_change < 0:
        trend_type = "снижение"
    else:
        trend_type = "стабильность"

    return {
        "success": True,
        "region": region_label,
        "period": {
            "start_year": start_year,
            "end_year": end_year,
            "years_span": year_span,
        },
        "population": {
            "start": start_population,
            "end": end_population,
            "start_formatted": f"{start_population:,}",
            "end_formatted": f"{end_population:,}",
        },
        "change": {
            "absolute": absolute_change,
            "absolute_formatted": f"{absolute_change:+,}",
            "percent": round(percent_change, 2),
            "percent_formatted": f"{percent_change:+.2f}%",
            "trend_type": trend_type,
        },
        "annual_growth": {
            "cagr_percent": round(annual_growth_rate, 2),
            "cagr_formatted": f"{annual_growth_rate:+.2f}%",
            "average_annual_change": round(absolute_change / year_span, 0) if year_span > 0 else 0,
        },
        "timestamp": datetime.now().isoformat(),
    }
