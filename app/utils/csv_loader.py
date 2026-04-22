import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

from app.config import settings

class CSVLoader:
    def __init__(self):
        self.data_cache: Dict[int, pd.DataFrame] = {}
        self.data_dir = Path(settings.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def load_year(self, year: int, force_reload: bool = False) -> Optional[pd.DataFrame]:
        if not force_reload and year in self.data_cache:
            logger.info(f"Using cached data for year {year}")
            return self.data_cache[year]
        
        file_path = self.data_dir / f"{year}.csv"
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        try:
            # Явно указываем разделитель и кодировку
            df = pd.read_csv(file_path, encoding=settings.CSV_ENCODING, sep=',')
            
            # Удаляем пробелы из названий колонок
            df.columns = df.columns.str.strip()
            
            logger.info(f"Loaded {year}.csv with columns: {df.columns.tolist()}")
            logger.info(f"First row: {df.iloc[0].to_dict()}")
            
            # Создаем новый DataFrame с едиными названиями колонок
            new_df = pd.DataFrame()
            new_df['name'] = df['name']
            new_df['total_population'] = df['population_year']
            new_df['urban_population'] = df['urban_year']
            new_df['rural_population'] = df['rural_year']
            new_df['year'] = year
            
            # Вычисляем urban_ratio
            new_df['urban_ratio'] = np.where(
                new_df['total_population'] > 0,
                new_df['urban_population'] / new_df['total_population'],
                0
            )
            
            self.data_cache[year] = new_df
            logger.info(f"Loaded {len(new_df)} records for year {year}")
            logger.info(f"First record: {new_df.iloc[0]['name']} - {new_df.iloc[0]['total_population']}")
            return new_df
            
        except Exception as e:
            logger.error(f"Error loading {year}.csv: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_available_years(self) -> List[int]:
        years = []
        for file_path in self.data_dir.glob("*.csv"):
            try:
                year = int(file_path.stem)
                years.append(year)
            except ValueError:
                continue
        return sorted(years)

csv_loader = CSVLoader()
