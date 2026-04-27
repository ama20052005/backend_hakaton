import hashlib
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.config import settings
from app.core.logging import logger


class CSVLoader:
    """Загрузчик CSV файлов по годам."""

    def __init__(self):
        self.data_cache: Dict[int, pd.DataFrame] = {}
        self.metadata: Dict = {}
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
            # Загружаем CSV и сразу удаляем пробелы из названий колонок
            df = pd.read_csv(file_path, encoding=settings.CSV_ENCODING)
            
            # Удаляем пробелы из названий колонок
            df.columns = df.columns.str.strip()
            
            logger.info(f"Columns after strip: {list(df.columns)}")
            
            # Создаем новый DataFrame с правильными колонками
            new_df = pd.DataFrame()
            new_df['name'] = df['name'].astype(str).str.strip()
            new_df['total_population'] = pd.to_numeric(df['population_year'], errors='coerce').fillna(0).astype(int)
            new_df['urban_population'] = pd.to_numeric(df['urban_year'], errors='coerce').fillna(0).astype(int)
            new_df['rural_population'] = pd.to_numeric(df['rural_year'], errors='coerce').fillna(0).astype(int)
            new_df['year'] = year
            
            # Создаем уникальный code на основе имени
            new_df['code'] = new_df['name'].apply(
                lambda x: f"entity-{hashlib.md5(x.encode()).hexdigest()[:12]}"
            )
            
            # Вычисляем urban_ratio
            new_df['urban_ratio'] = np.where(
                new_df['total_population'] > 0,
                new_df['urban_population'] / new_df['total_population'],
                0
            )
            
            self.data_cache[year] = new_df
            
            # Логируем данные РФ для проверки
            russia_row = new_df[new_df['name'].str.contains('Российская', case=False, na=False)]
            if not russia_row.empty:
                logger.info(f"✅ Loaded {year}: Russia population = {russia_row.iloc[0]['total_population']:,}")
            else:
                logger.warning(f"⚠️ Year {year}: No Russia row found")
            
            logger.info(f"Loaded {len(new_df)} total records for year {year}")
            return new_df
            
        except Exception as e:
            logger.error(f"Error loading {year}.csv: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_available_years(self) -> List[int]:
        """Возвращает список доступных годов."""
        years = set()
        for file_path in self.data_dir.glob("*.csv"):
            stem = file_path.stem
            try:
                year = int(stem)
            except ValueError:
                continue
            if 2012 <= year <= 2024:
                years.add(year)
        return sorted(years)


csv_loader = CSVLoader()
