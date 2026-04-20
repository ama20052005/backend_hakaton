# app/services/data_service.py
from typing import Dict, List, Optional, Any
import pandas as pd
from loguru import logger

from app.utils.csv_loader import csv_loader
from app.models import MunicipalityData, YearlyStatistic

class DataService:
    """Сервис для работы с демографическими данными"""
    
    def __init__(self):
        self.loader = csv_loader
    
    def get_data_for_year(self, year: int) -> Optional[pd.DataFrame]:
        """Получает DataFrame за указанный год"""
        return self.loader.load_year(year)
    
    def get_municipality(
        self, 
        code: str, 
        year: int = 2024
    ) -> Optional[MunicipalityData]:
        """Получает данные муниципального образования по коду"""
        df = self.loader.load_year(year)
        if df is None:
            return None
        
        row = df[df['code'].astype(str) == str(code)]
        if row.empty:
            return None
        
        return MunicipalityData(
            code=str(row.iloc[0]['code']),
            name=str(row.iloc[0]['name']),
            total_population=int(row.iloc[0]['total_population']),
            urban_population=int(row.iloc[0]['urban_population']),
            rural_population=int(row.iloc[0]['rural_population']),
            urban_ratio=float(row.iloc[0]['urban_ratio']),
            year=year
        )
    
    def search_municipality(
        self, 
        query: str, 
        year: int = 2024,
        limit: int = 10
    ) -> List[MunicipalityData]:
        """Ищет муниципальные образования по названию"""
        df = self.loader.load_year(year)
        if df is None:
            return []
        
        # Поиск по названию
        mask = df['name'].str.contains(query, case=False, na=False)
        results = df[mask].head(limit)
        
        return [
            MunicipalityData(
                code=str(row['code']),
                name=str(row['name']),
                total_population=int(row['total_population']),
                urban_population=int(row['urban_population']),
                rural_population=int(row['rural_population']),
                urban_ratio=float(row['urban_ratio']),
                year=year
            )
            for _, row in results.iterrows()
        ]
    
    def get_top_cities(
        self, 
        year: int = 2024, 
        n: int = 10
    ) -> List[MunicipalityData]:
        """Получает топ N городов по населению"""
        df = self.loader.load_year(year)
        if df is None:
            return []
        
        # Определяем города
        cities_df = df[df['code'].astype(str).str.contains('011000', na=False)]
        
        if len(cities_df) == 0:
            cities_df = df.nlargest(n, 'total_population')
        else:
            cities_df = cities_df.nlargest(n, 'total_population')
        
        return [
            MunicipalityData(
                code=str(row['code']),
                name=str(row['name']),
                total_population=int(row['total_population']),
                urban_population=int(row['urban_population']),
                rural_population=int(row['rural_population']),
                urban_ratio=float(row['urban_ratio']),
                year=year
            )
            for _, row in cities_df.iterrows()
        ]
    
    def get_regions(self, year: int = 2024) -> List[MunicipalityData]:
        """Получает список регионов (уровень субъектов РФ)"""
        df = self.loader.load_year(year)
        if df is None:
            return []
        
        # Регионы имеют коды, заканчивающиеся на 0000000
        regions_df = df[df['code'].astype(str).str.endswith('0000000')]
        
        return [
            MunicipalityData(
                code=str(row['code']),
                name=str(row['name']),
                total_population=int(row['total_population']),
                urban_population=int(row['urban_population']),
                rural_population=int(row['rural_population']),
                urban_ratio=float(row['urban_ratio']),
                year=year
            )
            for _, row in regions_df.iterrows()
        ]
    
    def get_year_statistics(self, year: int) -> Optional[YearlyStatistic]:
        """Получает общую статистику за год"""
        summary = self.loader.get_year_summary(year)
        if summary is None:
            return None
        
        return YearlyStatistic(
            year=summary['year'],
            total_population=summary['total_population'],
            urban_population=summary['urban_population'],
            rural_population=summary['rural_population'],
            urban_ratio=summary['average_urban_ratio'],
            number_of_municipalities=summary['number_of_municipalities']
        )
    
    def get_available_years(self) -> List[int]:
        """Получает список доступных годов"""
        return self.loader.get_available_years()
    
    def get_yearly_trends(self, years: List[int] = None) -> Dict:
        """Получает тренды за указанные годы"""
        if years is None:
            years = self.get_available_years()
        
        return self.loader.get_trends(years)

# Глобальный экземпляр
data_service = DataService()