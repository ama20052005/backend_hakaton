from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AnalysisType(str, Enum):
    POPULATION_SUMMARY = "population_summary"
    URBAN_RATIO = "urban_ratio"
    REGION_COMPARISON = "region_comparison"
    YEARLY_TREND = "yearly_trend"
    TOP_CITIES = "top_cities"
    BOTTOM_CITIES = "bottom_cities"
    REGION_DETAILS = "region_details"


class ReportFormat(str, Enum):
    DOCX = "docx"
    PDF = "pdf"
    BOTH = "both"


class ReportScope(str, Enum):
    RUSSIA = "russia"
    REGION = "region"


class TimeRange(BaseModel):
    start_year: int = Field(..., ge=2012, le=2024)
    end_year: int = Field(..., ge=2012, le=2024)

    @field_validator("end_year")
    @classmethod
    def validate_years(cls, value: int, info):
        start_year = info.data.get("start_year")
        if start_year is not None and value < start_year:
            raise ValueError("end_year must be >= start_year")
        return value


class QueryRequest(BaseModel):
    """Запрос к LLaMA"""

    prompt: str = Field(..., description="Текст запроса", min_length=1, max_length=4000)
    model: str = Field(default="llama3.2:3b", description="Модель LLaMA")
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1000, ge=1, le=4096)
    year: Optional[int] = Field(default=2024, description="Год данных для контекста")
    use_cache: bool = Field(default=True)

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "Какой процент населения России живет в городах?",
                "year": 2024,
                "temperature": 0.7,
            }
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

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "Покажи топ-10 городов России по численности населения",
                "analysis_type": "top_cities",
                "year": 2024,
            }
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
    """Модель территориальной единицы в текущем датасете."""

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
    average_urban_ratio: float = 0.0


class GrowthDeclineItem(BaseModel):
    name: str
    start_population: int
    end_population: int
    absolute_change: int
    percent_change: float


class GrowthDeclineResponse(BaseModel):
    start_year: int
    end_year: int
    growth: List[GrowthDeclineItem]
    decline: List[GrowthDeclineItem]


class ReportGenerationRequest(BaseModel):
    start_year: int = Field(..., ge=2012, le=2024)
    end_year: int = Field(..., ge=2012, le=2024)
    scope: ReportScope = Field(default=ReportScope.RUSSIA)
    region_name: Optional[str] = Field(
        default=None,
        description="Название региона для индивидуальной справки",
    )
    format: ReportFormat = Field(default=ReportFormat.BOTH)
    focus_prompt: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Дополнительный пользовательский акцент для AI-вывода",
    )
    include_ai_summary: bool = Field(default=True)
    model: Optional[str] = Field(default=None, description="Модель LLaMA для AI-блока")

    @field_validator("end_year")
    @classmethod
    def validate_end_year(cls, value: int, info):
        start_year = info.data.get("start_year")
        if start_year is not None and value < start_year:
            raise ValueError("end_year must be >= start_year")
        return value

    @model_validator(mode="after")
    def validate_scope(self):
        if self.scope == ReportScope.REGION and not self.region_name:
            raise ValueError("region_name is required when scope='region'")
        return self


class ReportMetric(BaseModel):
    label: str
    value: str


class ReportTable(BaseModel):
    title: str
    columns: List[str]
    rows: List[List[str]]


class ReportSection(BaseModel):
    heading: str
    paragraphs: List[str] = Field(default_factory=list)
    tables: List[ReportTable] = Field(default_factory=list)


class ReportPayload(BaseModel):
    report_id: str
    title: str
    subtitle: str
    generated_at: datetime
    scope: ReportScope
    parameters: Dict[str, str]
    summary_metrics: List[ReportMetric]
    sections: List[ReportSection]


class GeneratedReportFile(BaseModel):
    format: ReportFormat
    filename: str
    download_url: str
    content_type: str
    size_bytes: int


class ReportGenerationResponse(BaseModel):
    report_id: str
    title: str
    scope: ReportScope
    start_year: int
    end_year: int
    created_at: datetime
    files: List[GeneratedReportFile]


class HealthResponse(BaseModel):
    status: str
    version: str
    models_available: List[str]
    years_available: List[int]
    data_loaded: bool
    timestamp: datetime
