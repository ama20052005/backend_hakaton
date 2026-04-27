import pandas as pd
from typing import Optional, List, Dict
from loguru import logger

from app.utils.csv_loader import csv_loader

class DataService:
    def __init__(self):
        self.loader = csv_loader
    
    def _is_russia(self, name: str) -> bool:
        """Проверяет, является ли запись Российской Федерацией"""
        return 'Российская Феде' in str(name)
    
    def _filter_russia(self, df):
        """Исключает строку с Российской Федерацией"""
        return df[~df['name'].apply(self._is_russia)]
    
    def get_municipality(self, code: str, year: int = 2024):
        df = self.loader.load_year(year)
        if df is None:
            return None
        
        df_filtered = self._filter_russia(df)
        row = df_filtered[df_filtered['code'] == code]
        if row.empty:
            return None
        
        return {
            "code": str(row.iloc[0]['code']),
            "name": str(row.iloc[0]['name']),
            "total_population": int(row.iloc[0]['total_population']),
            "urban_population": int(row.iloc[0]['urban_population']),
            "rural_population": int(row.iloc[0]['rural_population']),
            "urban_ratio": float(row.iloc[0]['urban_ratio']),
            "year": year
        }
    
    def search_municipality(self, query: str, year: int = 2024, limit: int = 10) -> List[Dict]:
        df = self.loader.load_year(year)
        if df is None:
            return []
        
        df_filtered = self._filter_russia(df)
        mask = df_filtered['name'].str.contains(query, case=False, na=False)
        results = df_filtered[mask].head(limit)
        
        return [
            {
                "code": str(row['code']),
                "name": str(row['name']),
                "total_population": int(row['total_population']),
                "urban_population": int(row['urban_population']),
                "rural_population": int(row['rural_population']),
                "urban_ratio": float(row['urban_ratio']),
                "year": year
            }
            for _, row in results.iterrows()
        ]
    
    def get_top_cities(self, year: int = 2024, limit: int = 10) -> List[Dict]:
        """Возвращает топ N городов/регионов по населению (исключая РФ)"""
        df = self.loader.load_year(year)
        if df is None:
            return []
        
        df_filtered = self._filter_russia(df)
        top_regions = df_filtered.nlargest(limit, 'total_population')
        
        return [
            {
                "code": str(row['code']),
                "name": str(row['name']),
                "total_population": int(row['total_population']),
                "urban_population": int(row['urban_population']),
                "rural_population": int(row['rural_population']),
                "urban_ratio": float(row['urban_ratio']),
                "year": year
            }
            for _, row in top_regions.iterrows()
        ]
    
    def get_regions(self, year: int = 2024) -> List[Dict]:
        """Возвращает список регионов (исключая РФ)"""
        df = self.loader.load_year(year)
        if df is None:
            return []
        
        df_filtered = self._filter_russia(df)
        
        return [
            {
                "code": str(row['code']),
                "name": str(row['name']),
                "total_population": int(row['total_population']),
                "urban_population": int(row['urban_population']),
                "rural_population": int(row['rural_population']),
                "urban_ratio": float(row['urban_ratio']),
                "year": year
            }
            for _, row in df_filtered.iterrows()
        ]
    
    def get_yearly_trends(self, years: List[int]) -> Dict:
        """Получает тренды за указанные годы (берёт данные из строки РФ)"""
        trends = {
            "years": [],
            "total_population": [],
            "urban_population": [],
            "rural_population": []
        }
        
        for year in sorted(years):
            # Берём данные РФ напрямую из CSV
            df = self.loader.load_year(year)
            if df is not None:
                # Ищем строку с РФ
                russia_mask = df['name'].apply(self._is_russia)
                russia_row = df[russia_mask]
                
                if not russia_row.empty:
                    trends["years"].append(year)
                    trends["total_population"].append(int(russia_row.iloc[0]['total_population']))
                    trends["urban_population"].append(int(russia_row.iloc[0]['urban_population']))
                    trends["rural_population"].append(int(russia_row.iloc[0]['rural_population']))
                    logger.info(f"Trends {year}: {int(russia_row.iloc[0]['total_population']):,}")
                else:
                    logger.warning(f"No Russia row found for {year}")
        
        if len(trends["total_population"]) >= 2:
            first_pop = trends["total_population"][0]
            last_pop = trends["total_population"][-1]
            growth_rate = ((last_pop - first_pop) / first_pop) * 100 if first_pop > 0 else 0
        else:
            growth_rate = 0
        
        trends["growth_rate"] = round(growth_rate, 2)
        return trends
    
    def get_available_years(self) -> List[int]:
        return self.loader.get_available_years()
    
    def get_year_statistics(self, year: int):
        """Берёт данные ТОЛЬКО из строки РФ"""
        df = self.loader.load_year(year)
        if df is None:
            return None
        
        # Ищем строку с РФ
        russia_mask = df['name'].apply(self._is_russia)
        russia_row = df[russia_mask]
        
        if russia_row.empty:
            logger.error(f"Нет строки РФ за {year} год")
            return None
        
        # Берём данные из строки РФ
        total_pop = int(russia_row.iloc[0]['total_population'])
        urban_pop = int(russia_row.iloc[0]['urban_population'])
        rural_pop = int(russia_row.iloc[0]['rural_population'])
        
        logger.info(f"Russia data for {year}: {total_pop:,}")
        
        # Количество муниципалитетов (без РФ)
        df_filtered = self._filter_russia(df)
        num_municipalities = len(df_filtered)
        
        return {
            "year": year,
            "total_population": total_pop,
            "urban_population": urban_pop,
            "rural_population": rural_pop,
            "urban_ratio": urban_pop / total_pop if total_pop > 0 else 0,
            "number_of_municipalities": num_municipalities
        }
    
    def get_all_data(self, year: int = 2024):
        return self.loader.load_year(year)


data_service = DataService()
