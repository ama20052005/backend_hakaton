# app/services/analysis_service.py
from typing import Dict, List, Optional, Any
import pandas as pd

from app.services.data_service import data_service
from app.services.llama_service import llama_service
from app.models import AnalysisType, DataAnalysisRequest

class AnalysisService:
    """Сервис для анализа данных с помощью LLaMA"""
    
    def __init__(self):
        self.data_service = data_service
        self.llama_service = llama_service
    
    async def analyze(self, request: DataAnalysisRequest) -> str:
        """Анализирует данные согласно запросу"""
        
        # Получаем данные в зависимости от типа анализа
        context = await self._build_context(request)
        
        # Формируем промпт
        prompt = self._build_prompt(request, context)
        
        # Отправляем в LLaMA
        result = await self.llama_service.generate(
            prompt=prompt,
            year=request.year,
            use_cache=True
        )
        
        return result.get("response", "Не удалось выполнить анализ")
    
    async def _build_context(self, request: DataAnalysisRequest) -> str:
        """Строит контекст на основе типа анализа"""
        
        if request.analysis_type == AnalysisType.POPULATION_SUMMARY:
            return await self._get_population_summary(request.year)
        
        elif request.analysis_type == AnalysisType.TOP_CITIES:
            return await self._get_top_cities_context(request.year)
        
        elif request.analysis_type == AnalysisType.REGION_COMPARISON:
            return await self._get_region_comparison(request.year)
        
        elif request.analysis_type == AnalysisType.YEARLY_TREND:
            return await self._get_yearly_trends(request.compare_years)
        
        elif request.analysis_type == AnalysisType.REGION_DETAILS:
            return await self._get_region_details(request.region_code, request.year)
        
        else:
            # Общий контекст
            return await self._get_general_context(request.year)
    
    async def _get_population_summary(self, year: int) -> str:
        """Получает сводку по населению"""
        stats = self.data_service.get_year_statistics(year)
        if not stats:
            return f"Данные за {year} год не найдены"
        
        return f"""
ОБЩАЯ СТАТИСТИКА ЗА {year} ГОД:
- Общая численность населения: {stats.total_population:,} человек
- Городское население: {stats.urban_population:,} человек
- Сельское население: {stats.rural_population:,} человек
- Доля городского населения: {stats.urban_ratio:.1%}
- Количество муниципальных образований: {stats.number_of_municipalities}
"""
    
    async def _get_top_cities_context(self, year: int, n: int = 10) -> str:
        """Получает контекст топ городов"""
        top_cities = self.data_service.get_top_cities(year, n)
        
        if not top_cities:
            return f"Данные за {year} год не найдены"
        
        context = f"ТОП-{n} ГОРОДОВ ПО НАСЕЛЕНИЮ ЗА {year} ГОД:\n\n"
        for i, city in enumerate(top_cities, 1):
            context += f"{i}. {city.name}: {city.total_population:,} чел.\n"
        
        return context
    
    async def _get_region_comparison(self, year: int) -> str:
        """Получает сравнение регионов"""
        regions = self.data_service.get_regions(year)
        
        if not regions:
            return f"Данные за {year} год не найдены"
        
        # Сортируем по населению
        regions_sorted = sorted(regions, key=lambda x: x.total_population, reverse=True)
        top_regions = regions_sorted[:10]
        
        context = f"КРУПНЕЙШИЕ РЕГИОНЫ ПО НАСЕЛЕНИЮ ЗА {year} ГОД:\n\n"
        for i, region in enumerate(top_regions, 1):
            context += f"{i}. {region.name}: {region.total_population:,} чел. (городское: {region.urban_ratio:.1%})\n"
        
        return context
    
    async def _get_yearly_trends(self, time_range) -> str:
        """Получает тренды по годам"""
        if not time_range:
            return "Не указан период для анализа трендов"
        
        trends = self.data_service.get_yearly_trends(
            list(range(time_range.start_year, time_range.end_year + 1))
        )
        
        if not trends.get('years'):
            return f"Данные за период {time_range.start_year}-{time_range.end_year} не найдены"
        
        context = f"ДИНАМИКА НАСЕЛЕНИЯ ЗА {time_range.start_year}-{time_range.end_year} ГГ.:\n\n"
        
        for i, year in enumerate(trends['years']):
            context += f"{year}: {trends['total_population'][i]:,} чел.\n"
        
        context += f"\nОБЩИЙ ТЕМП РОСТА ЗА ПЕРИОД: {trends.get('growth_rate', 0):.1f}%\n"
        
        return context
    
    async def _get_region_details(self, region_code: str, year: int) -> str:
        """Получает детали по региону"""
        if not region_code:
            return "Не указан код региона"
        
        region = self.data_service.get_municipality(region_code, year)
        if not region:
            return f"Регион с кодом {region_code} не найден за {year} год"
        
        return f"""
ИНФОРМАЦИЯ О РЕГИОНЕ: {region.name} ({year} г.)

- Общая численность населения: {region.total_population:,} чел.
- Городское население: {region.urban_population:,} чел.
- Сельское население: {region.rural_population:,} чел.
- Уровень урбанизации: {region.urban_ratio:.1%}
"""
    
    async def _get_general_context(self, year: int) -> str:
        """Получает общий контекст"""
        stats = self.data_service.get_year_statistics(year)
        if not stats:
            return f"Данные за {year} год не найдены"
        
        return f"""
ДЕМОГРАФИЧЕСКИЕ ДАННЫЕ РОССИИ ЗА {year} ГОД:

Общая численность населения: {stats.total_population:,} человек
Городское население: {stats.urban_population:,} человек ({stats.urban_ratio:.1%})
Сельское население: {stats.rural_population:,} человек
"""
    
    def _build_prompt(self, request: DataAnalysisRequest, context: str) -> str:
        """Строит промпт для LLaMA"""
        
        return f"""Ты - эксперт по демографической статистике России. Используй предоставленные данные для ответа на вопрос пользователя.

{context}

ВОПРОС ПОЛЬЗОВАТЕЛЯ: {request.question}

Пожалуйста, дай развернутый ответ, используя конкретные цифры из контекста. Если вопрос требует сравнения, приведи анализ. Будь точным и информативным.

ОТВЕТ:"""

# Глобальный экземпляр
analysis_service = AnalysisService()
