from fastapi import APIRouter, HTTPException, Query

from app.services.data_service import data_service

router = APIRouter(prefix="/data", tags=["data"])

@router.get("/years")
async def get_available_years():
    """Получить список доступных годов"""
    years = data_service.get_available_years()
    return {"years": years, "count": len(years)}

@router.get("/summary/{year}")
async def get_year_summary(year: int):
    """Получить сводку за год"""
    if year < 2012 or year > 2024:
        raise HTTPException(status_code=400, detail="Year must be between 2012 and 2024")
    
    stats = data_service.get_year_statistics(year)
    if not stats:
        raise HTTPException(status_code=404, detail=f"Data for year {year} not found")
    
    return stats

@router.get("/municipality/{code}")
async def get_municipality(
    code: str, 
    year: int = Query(2024, ge=2012, le=2024)
):
    """Получить данные муниципального образования по коду"""
    data = data_service.get_municipality(code, year)
    if not data:
        raise HTTPException(status_code=404, detail=f"Municipality with code {code} not found for year {year}")
    
    return data

@router.get("/search")
async def search_municipality(
    query: str,
    year: int = Query(2024, ge=2012, le=2024),
    limit: int = Query(10, ge=1, le=100)
):
    """Поиск муниципальных образований по названию"""
    results = data_service.search_municipality(query, year, limit)
    return {"results": results, "count": len(results)}

@router.get("/top-cities/{year}")
async def get_top_cities(
    year: int,
    limit: int = Query(10, ge=1, le=50)
):
    """Получить топ N регионов по населению без строки по России"""
    cities = data_service.get_top_cities(year, limit)
    return {"year": year, "cities": cities, "count": len(cities)}

@router.get("/regions/{year}")
async def get_regions(year: int):
    """Получить список регионов за год без агрегированной строки по России"""
    regions = data_service.get_regions(year)
    return {"year": year, "regions": regions, "count": len(regions)}

@router.get("/trends")
async def get_trends(
    start_year: int = Query(2012, ge=2012, le=2024),
    end_year: int = Query(2024, ge=2012, le=2024)
):
    """Получить тренды за период"""
    if start_year > end_year:
        raise HTTPException(status_code=400, detail="start_year must be <= end_year")
    
    trends = data_service.get_yearly_trends(list(range(start_year, end_year + 1)))
    return trends
