# app/models.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum

class AnalysisType(str, Enum):
    POPULATION_SUMMARY = "population_summary"
    URBAN_RATIO = "urban_ratio"
    REGION_COMPARISON = "region_comparison"
    YEARLY_TREND = "yearly_trend"
    TOP_CITIES = "top_cities"
    BOTTOM_CITIES = "bottom_cities"
    REGION_DETAILS = "region_details"

class TimeRange(BaseModel):
    start_year: int = Field(..., ge=2012, le=2024)
    end_year: int = Field(..., ge=2012, le=2024)
    
    @validator('end_year')
    def validate_years(cls, v, values):
        if 'start_year' in values and v < values['start_year']:
            raise ValueError('end_year must be >= start_year')
        return v

class QueryRequest(BaseModel):
    """Запрос к LLaMA"""
    prompt: str = Field(..., description="Текст запроса", min_length=1, max_length=4000)
    model: str = Field(default="llama3.2:3b", description="Модель LLaMA")
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1000, ge=1, le=4096)
    year: Optional[int] = Field(default=2024, description="Год данных для контекста")
    use_cache: bool = Field(default=True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Какой процент населения России живет в городах?",
                "year": 2024,
                "temperature": 0.7
            }
        }

class DataAnalysisRequest(BaseModel):
    """Запрос на анализ данных"""
    question: str = Field(..., description="Вопрос о демографических данных")
    analysis_type: AnalysisType = Field(default=AnalysisType.POPULATION_SUMMARY)
    year: int = Field(default=2024, ge=2012, le=2024)
    compare_years: Optional[TimeRange] = None
    region_code: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "Покажи топ-10 городов России по численности населения",
                "analysis_type": "top_cities",
                "year": 2024
            }
        }

class QueryResponse(BaseModel):
    """Ответ от LLaMA"""
    answer: str
    model_used: str
    year_used: int
    processing_time: float
    timestamp: datetime
    cached: bool = False
    tokens_used: Optional[int] = None

class MunicipalityData(BaseModel):
    """Модель муниципальных данных"""
    code: str
    name: str
    total_population: int
    urban_population: int
    rural_population: int
    urban_ratio: float
    year: int

class YearlyStatistic(BaseModel):
    year: int
    total_population: int
    urban_population: int
    rural_population: int
    urban_ratio: float
    number_of_municipalities: int

class TrendAnalysis(BaseModel):
    years: List[int]
    total_population: List[int]
    urban_population: List[int]
    rural_population: List[int]
    growth_rate: float
    average_urban_ratio: float

class HealthResponse(BaseModel):
    status: str
    version: str
    models_available: List[str]
    years_available: List[int]
    data_loaded: bool
    timestamp: datetime