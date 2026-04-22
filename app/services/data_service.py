import pandas as pd
from typing import Optional, List, Dict
from loguru import logger

from app.utils.csv_loader import csv_loader

class DataService:
    def __init__(self):
        self.loader = csv_loader
    
    def get_municipality(self, code: str, year: int = 2024):
        df = self.loader.load_year(year)
        if df is None:
            return None
        
        if 'code' not in df.columns:
            df['code'] = df.index.astype(str)
        
        row = df[df['code'] == code]
        
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
        
        mask = df['name'].str.contains(query, case=False, na=False)
        results = df[mask].head(limit)
        
        return [
            {
                "code": str(idx),
                "name": str(row['name']),
                "total_population": int(row['total_population']),
                "urban_population": int(row['urban_population']),
                "rural_population": int(row['rural_population']),
                "urban_ratio": float(row['urban_ratio']),
                "year": year
            }
            for idx, row in results.iterrows()
        ]
    
    def get_top_cities(self, year: int = 2024, limit: int = 10) -> List[Dict]:
        df = self.loader.load_year(year)
        if df is None:
            return []
        
        top_regions = df.nlargest(limit, 'total_population')
        
        return [
            {
                "code": str(idx),
                "name": str(row['name']),
                "total_population": int(row['total_population']),
                "urban_population": int(row['urban_population']),
                "rural_population": int(row['rural_population']),
                "urban_ratio": float(row['urban_ratio']),
                "year": year
            }
            for idx, row in top_regions.iterrows()
        ]
    
    def get_regions(self, year: int = 2024) -> List[Dict]:
        df = self.loader.load_year(year)
        if df is None:
            return []
        
        return [
            {
                "code": str(idx),
                "name": str(row['name']),
                "total_population": int(row['total_population']),
                "urban_population": int(row['urban_population']),
                "rural_population": int(row['rural_population']),
                "urban_ratio": float(row['urban_ratio']),
                "year": year
            }
            for idx, row in df.iterrows()
        ]
    
    def get_yearly_trends(self, years: List[int]) -> Dict:
        trends = {
            "years": [],
            "total_population": [],
            "urban_population": [],
            "rural_population": []
        }
        
        for year in sorted(years):
            df = self.loader.load_year(year)
            if df is not None:
                trends["years"].append(year)
                trends["total_population"].append(int(df['total_population'].sum()))
                trends["urban_population"].append(int(df['urban_population'].sum()))
                trends["rural_population"].append(int(df['rural_population'].sum()))
        
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
        df = self.loader.load_year(year)
        if df is None:
            return None
        
        total_pop = df['total_population'].sum()
        urban_pop = df['urban_population'].sum()
        
        return {
            "year": year,
            "total_population": int(total_pop),
            "urban_population": int(urban_pop),
            "rural_population": int(total_pop - urban_pop),
            "urban_ratio": urban_pop / total_pop if total_pop > 0 else 0,
            "number_of_municipalities": len(df)
        }
    
    def get_all_data(self, year: int = 2024):
        return self.loader.load_year(year)

data_service = DataService()
