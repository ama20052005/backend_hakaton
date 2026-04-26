from fastapi import APIRouter, HTTPException, Query

from app.models import GrowthDeclineResponse
from app.services.trends_service import trends_service

router = APIRouter(prefix="/trends", tags=["trends"])


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
