# app/api/routes/analysis.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.models import (
    QueryRequest, 
    QueryResponse, 
    DataAnalysisRequest,
    AnalysisType
)
from app.services.llama_service import llama_service
from app.services.analysis_service import analysis_service
from app.services.data_service import data_service

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("/query", response_model=QueryResponse)
async def query_llama(request: QueryRequest):
    """
    Отправить запрос к LLaMA с контекстом демографических данных
    """
    # Получаем контекст данных за указанный год
    year_stats = data_service.get_year_statistics(request.year)
    
    if year_stats:
        context = f"""
ДЕМОГРАФИЧЕСКИЕ ДАННЫЕ РОССИИ ЗА {request.year} ГОД:
- Общая численность населения: {year_stats.total_population:,} человек
- Городское население: {year_stats.urban_population:,} человек
- Сельское население: {year_stats.rural_population:,} человек
- Доля городского населения: {year_stats.urban_ratio:.1%}
"""
        prompt = f"{context}\n\nВОПРОС: {request.prompt}\n\nОТВЕТ:"
    else:
        prompt = request.prompt
    
    result = await llama_service.generate(
        prompt=prompt,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        year=request.year,
        use_cache=request.use_cache
    )
    
    return QueryResponse(
        answer=result.get("response", ""),
        model_used=result.get("model", request.model),
        year_used=request.year,
        processing_time=result.get("processing_time", 0),
        timestamp=result.get("timestamp", datetime.now()),
        cached=result.get("cached", False)
    )

@router.post("/analyze", response_model=QueryResponse)
async def analyze_data(request: DataAnalysisRequest):
    """
    Анализ демографических данных с помощью LLaMA
    """
    try:
        answer = await analysis_service.analyze(request)
        
        return QueryResponse(
            answer=answer,
            model_used=settings.DEFAULT_MODEL,
            year_used=request.year,
            processing_time=0,
            timestamp=datetime.now(),
            cached=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suggestions")
async def get_analysis_suggestions():
    """
    Получить примеры запросов для анализа
    """
    suggestions = [
        {
            "question": "Как изменилась численность населения России за последние 5 лет?",
            "analysis_type": AnalysisType.YEARLY_TREND,
            "description": "Анализ динамики населения"
        },
        {
            "question": "Назови топ-5 городов России по численности населения",
            "analysis_type": AnalysisType.TOP_CITIES,
            "description": "Список крупнейших городов"
        },
        {
            "question": "В каких регионах самый высокий уровень урбанизации?",
            "analysis_type": AnalysisType.REGION_COMPARISON,
            "description": "Сравнение регионов"
        },
        {
            "question": "Какой процент населения России живет в городах?",
            "analysis_type": AnalysisType.POPULATION_SUMMARY,
            "description": "Общая демографическая картина"
        }
    ]
    
    return {"suggestions": suggestions}