# app/utils/csv_loader.py
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger
import json
from datetime import datetime

from app.config import settings

class CSVLoader:
    """Загрузчик CSV файлов по годам"""
    
    def __init__(self):
        self.data_cache: Dict[int, pd.DataFrame] = {}
        self.metadata: Dict = {}
        self.data_dir = Path(settings.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def load_year(self, year: int, force_reload: bool = False) -> Optional[pd.DataFrame]:
        """Загружает CSV файл за указанный год"""
        
        if not force_reload and year in self.data_cache:
            logger.info(f"Using cached data for year {year}")
            return self.data_cache[year]
        
        file_path = self.data_dir / f"{year}.csv"
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        try:
            df = pd.read_csv(file_path, encoding=settings.CSV_ENCODING)
            
            # Очистка и нормализация данных
            df = self._clean_dataframe(df, year)
            
            self.data_cache[year] = df
            logger.info(f"Loaded {len(df)} records for year {year}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading {year}.csv: {e}")
            return None
    
    def _clean_dataframe(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Очищает и нормализует DataFrame"""
        
        # Переименовываем колонки
        column_mapping = {
            'Коды территорий': 'code',
            'Все население': 'total_population',
            'городское население': 'urban_population',
            'сельское население': 'rural_population'
        }
        
        # Если колонки на русском, переименовываем
        if 'Все население' in df.columns:
            df = df.rename(columns=column_mapping)
        
        # Определяем колонку с названием (может быть разной)
        name_col = None
        for col in df.columns:
            if col.lower() in ['наименование', 'name', 'муниципальное образование']:
                name_col = col
                break
        
        if name_col and name_col != 'name':
            df = df.rename(columns={name_col: 'name'})
        
        # Добавляем год
        df['year'] = year
        
        # Конвертируем числовые колонки
        numeric_cols = ['total_population', 'urban_population', 'rural_population']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # Добавляем urban_ratio
        if 'urban_population' in df.columns and 'total_population' in df.columns:
            df['urban_ratio'] = np.where(
                df['total_population'] > 0,
                df['urban_population'] / df['total_population'],
                0
            )
        
        return df
    
    def load_multiple_years(self, years: List[int]) -> Dict[int, pd.DataFrame]:
        """Загружает данные за несколько лет"""
        result = {}
        for year in years:
            df = self.load_year(year)
            if df is not None:
                result[year] = df
        return result
    
    def get_available_years(self) -> List[int]:
        """Возвращает список доступных годов"""
        years = []
        for file_path in self.data_dir.glob("*.csv"):
            try:
                year = int(file_path.stem)
                if 2012 <= year <= 2024:
                    years.append(year)
            except ValueError:
                continue
        return sorted(years)
    
    def get_year_summary(self, year: int) -> Optional[Dict]:
        """Получает сводку по году"""
        df = self.load_year(year)
        if df is None:
            return None
        
        return {
            'year': year,
            'total_population': int(df['total_population'].sum()),
            'urban_population': int(df['urban_population'].sum()),
            'rural_population': int(df['rural_population'].sum()),
            'number_of_municipalities': len(df),
            'average_urban_ratio': float(df['urban_ratio'].mean()),
            'top_cities': self._get_top_cities(df, 10)
        }
    
    def _get_top_cities(self, df: pd.DataFrame, n: int = 10) -> List[Dict]:
        """Получает топ N городов"""
        # Определяем города по коду или названию
        cities_df = df[df['code'].astype(str).str.contains('011000', na=False)]
        
        if len(cities_df) == 0:
            # Если не нашли по коду, берем все записи с небольшим населением? 
            cities_df = df.nlargest(n, 'total_population')
        
        return cities_df.nlargest(n, 'total_population')[
            ['name', 'total_population', 'urban_population', 'rural_population']
        ].to_dict('records')
    
    def get_trends(self, years: List[int]) -> Dict:
        """Получает тренды за несколько лет"""
        trends = {
            'years': [],
            'total_population': [],
            'urban_population': [],
            'rural_population': []
        }
        
        for year in sorted(years):
            summary = self.get_year_summary(year)
            if summary:
                trends['years'].append(year)
                trends['total_population'].append(summary['total_population'])
                trends['urban_population'].append(summary['urban_population'])
                trends['rural_population'].append(summary['rural_population'])
        
        # Рассчитываем темпы роста
        if len(trends['total_population']) >= 2:
            first_pop = trends['total_population'][0]
            last_pop = trends['total_population'][-1]
            trends['growth_rate'] = ((last_pop - first_pop) / first_pop) * 100 if first_pop > 0 else 0
        else:
            trends['growth_rate'] = 0
        
        return trends

# Глобальный экземпляр
csv_loader = CSVLoader()