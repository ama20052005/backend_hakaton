import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from app.config import settings

class DemographicService:
    def __init__(self):
        self.data_dir = Path(settings.DATA_DIR)  # data/yearly
        self._birth_death_data = None
        self._migration_data = None
    
    def _load_birth_death(self):
        """Загружает данные о рождаемости и смертности"""
        if self._birth_death_data is not None:
            return self._birth_death_data
        
        # Пробуем разные имена файлов
        for filename in ["birth_death.csv", "prirost.csv"]:
            file_path = self.data_dir / filename
            if file_path.exists():
                df = pd.read_csv(file_path, encoding='utf-8-sig')
                df.columns = df.columns.str.strip()
                self._birth_death_data = df
                logger.info(f"Loaded birth/death data from {filename}")
                return df
        
        logger.error("Birth/death data file not found")
        return None
    
    def _load_migration(self):
        """Загружает данные о миграции"""
        if self._migration_data is not None:
            return self._migration_data
        
        for filename in ["migration.csv", "migr.csv"]:
            file_path = self.data_dir / filename
            if file_path.exists():
                df = pd.read_csv(file_path, encoding='utf-8-sig')
                df.columns = df.columns.str.strip()
                self._migration_data = df
                logger.info(f"Loaded migration data from {filename}")
                return df
        
        logger.error("Migration data file not found")
        return None
    
    def get_birth_death_by_year(self, year: int) -> Optional[Dict]:
        """Получает данные о рождаемости и смертности за конкретный год"""
        df = self._load_birth_death()
        if df is None:
            return None
        
        # Ищем строку с годом (очищаем от возможных примечаний)
        row = df[df['Годы'].astype(str).str.startswith(str(year))]
        if row.empty:
            return None
        
        return {
            "year": year,
            "births": int(row.iloc[0]['родившихся']),
            "deaths": int(row.iloc[0]['умерших']),
            "natural_increase": int(row.iloc[0]['естественныйприрост']),
            "birth_rate": float(row.iloc[0]['родившихсяна1000человек']),
            "death_rate": float(row.iloc[0]['умершихна1000человек']),
            "natural_increase_rate": float(row.iloc[0]['естественныйприростна1000человек'])
        }
    
    def get_migration_by_year(self, year: int) -> Optional[Dict]:
        """Получает данные о миграции за конкретный год"""
        df = self._load_migration()
        if df is None:
            return None
        
        row = df[df['Годы'].astype(str).str.startswith(str(year))]
        if row.empty:
            return None
        
        return {
            "year": year,
            "arrived": int(row.iloc[0]['Прибывшие - всего']),
            "departed": int(row.iloc[0]['Выбывшие - всего']),
            "migration_growth": int(row.iloc[0]['Миграционный прирост'])
        }
    
    def get_demographic_indicators(self, year: int) -> Dict:
        """Получает все демографические показатели за год"""
        birth_death = self.get_birth_death_by_year(year)
        migration = self.get_migration_by_year(year)
        
        result = {"year": year}
        
        if birth_death:
            result.update({
                "births": birth_death["births"],
                "deaths": birth_death["deaths"],
                "natural_increase": birth_death["natural_increase"],
                "birth_rate": birth_death["birth_rate"],
                "death_rate": birth_death["death_rate"],
                "natural_increase_rate": birth_death["natural_increase_rate"]
            })
        
        if migration:
            result.update({
                "arrived": migration["arrived"],
                "departed": migration["departed"],
                "migration_growth": migration["migration_growth"]
            })
        
        return result
    
    def get_available_years(self) -> List[int]:
        """Возвращает доступные годы для демографических данных"""
        df = self._load_birth_death()
        if df is None:
            return []
        
        years = []
        for val in df['Годы']:
            try:
                # Извлекаем год из строки (может быть "2023 5)")
                year_str = str(val).split()[0]
                year = int(year_str)
                if year >= 1950:
                    years.append(year)
            except:
                continue
        
        return sorted(set(years))

demographic_service = DemographicService()
