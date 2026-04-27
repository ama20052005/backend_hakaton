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
        """Загружает CSV файл за указанный год."""

        if not force_reload and year in self.data_cache:
            logger.info(f"Using cached data for year {year}")
            return self.data_cache[year]

        file_path = self._resolve_file_path(year)
        if file_path is None:
            logger.error(f"CSV file for year {year} not found in {self.data_dir}")
            return None

        try:
            df = pd.read_csv(file_path, encoding=settings.CSV_ENCODING)
            df = self._clean_dataframe(df, year)
            self.data_cache[year] = df
            logger.info(f"Loaded {len(df)} records for year {year} from {file_path.name}")
            return df
        except Exception as exc:
            logger.error(f"Error loading {file_path.name}: {exc}")
            return None

    def _resolve_file_path(self, year: int) -> Optional[Path]:
        """Поддерживает оба формата имени файла: YYYY.csv и data_YYYY.csv."""

        candidates = [
            self.data_dir / f"{year}.csv",
            self.data_dir / f"data_{year}.csv",
        ]
        for file_path in candidates:
            if file_path.exists():
                return file_path
        return None

    def _build_entity_code(self, name: str) -> str:
        normalized = name.strip().lower().encode("utf-8")
        return f"entity-{hashlib.md5(normalized).hexdigest()[:12]}"

    def _is_russia_name(self, name: str) -> bool:
        normalized = str(name).strip().lower()
        return "российская феде" in normalized

    def _filter_russia(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[~df["name"].apply(self._is_russia_name)]

    def _clean_dataframe(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Очищает и нормализует DataFrame под единый контракт API."""

        df = df.copy()
        df.columns = [str(column).strip() for column in df.columns]

        column_mapping = {
            "Коды территорий": "code",
            "Все население": "total_population",
            "городское население": "urban_population",
            "сельское население": "rural_population",
            "population_year": "total_population",
            "urban_year": "urban_population",
            "rural_year": "rural_population",
            "population_mean": "mean_total_population",
            "urban_mean": "mean_urban_population",
            "rural_mean": "mean_rural_population",
        }
        rename_map = {
            source: target
            for source, target in column_mapping.items()
            if source in df.columns
        }
        if rename_map:
            df = df.rename(columns=rename_map)

        name_col = None
        for column in df.columns:
            if column.lower() in {"наименование", "name", "муниципальное образование"}:
                name_col = column
                break

        if name_col is None:
            raise ValueError("CSV does not contain a supported name column")
        if name_col != "name":
            df = df.rename(columns={name_col: "name"})

        df["name"] = df["name"].astype(str).str.strip()

        if "code" not in df.columns:
            df["code"] = df["name"].apply(self._build_entity_code)
        else:
            df["code"] = df["code"].astype(str).str.strip()
            empty_mask = df["code"].eq("") | df["code"].eq("nan")
            df.loc[empty_mask, "code"] = df.loc[empty_mask, "name"].apply(self._build_entity_code)

        numeric_columns = ["total_population", "urban_population", "rural_population"]
        for column in numeric_columns:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)

        if "rural_population" not in df.columns and {
            "total_population",
            "urban_population",
        }.issubset(df.columns):
            df["rural_population"] = df["total_population"] - df["urban_population"]

        missing_required = [
            column
            for column in ["total_population", "urban_population", "rural_population"]
            if column not in df.columns
        ]
        if missing_required:
            raise ValueError(f"CSV is missing required columns: {', '.join(missing_required)}")

        df["year"] = year
        df["urban_ratio"] = np.where(
            df["total_population"] > 0,
            df["urban_population"] / df["total_population"],
            0,
        )

        return df

    def load_multiple_years(self, years: List[int]) -> Dict[int, pd.DataFrame]:
        """Загружает данные за несколько лет."""

        result = {}
        for year in years:
            df = self.load_year(year)
            if df is not None:
                result[year] = df
        return result

    def get_available_years(self) -> List[int]:
        """Возвращает список доступных годов."""

        years = set()
        for file_path in self.data_dir.glob("*.csv"):
            stem = file_path.stem
            if stem.startswith("data_"):
                stem = stem.removeprefix("data_")
            try:
                year = int(stem)
            except ValueError:
                continue
            if 2012 <= year <= 2024:
                years.add(year)
        return sorted(years)

    def get_year_summary(self, year: int) -> Optional[Dict]:
        """Получает сводку по году."""

        df = self.load_year(year)
        if df is None:
            return None

        russia_rows = df[df["name"].apply(self._is_russia_name)]
        filtered_df = self._filter_russia(df)

        if not russia_rows.empty:
            russia_row = russia_rows.iloc[0]
            return {
                "year": year,
                "total_population": int(russia_row["total_population"]),
                "urban_population": int(russia_row["urban_population"]),
                "rural_population": int(russia_row["rural_population"]),
                "number_of_municipalities": len(filtered_df),
                "average_urban_ratio": float(russia_row["urban_ratio"]),
                "top_cities": self._get_top_cities(filtered_df, 10),
            }

        return {
            "year": year,
            "total_population": int(df["total_population"].sum()),
            "urban_population": int(df["urban_population"].sum()),
            "rural_population": int(df["rural_population"].sum()),
            "number_of_municipalities": len(filtered_df),
            "average_urban_ratio": float(df["urban_ratio"].mean()),
            "top_cities": self._get_top_cities(filtered_df, 10),
        }

    def _get_top_cities(self, df: pd.DataFrame, n: int = 10) -> List[Dict]:
        """Возвращает крупнейшие записи датасета по населению."""

        filtered_df = self._filter_russia(df)
        return filtered_df.nlargest(n, "total_population")[
            ["name", "total_population", "urban_population", "rural_population"]
        ].to_dict("records")

    def get_trends(self, years: List[int]) -> Dict:
        """Получает тренды за несколько лет."""

        trends = {
            "years": [],
            "total_population": [],
            "urban_population": [],
            "rural_population": [],
        }
        urban_ratios: List[float] = []

        for year in sorted(years):
            summary = self.get_year_summary(year)
            if summary:
                trends["years"].append(year)
                trends["total_population"].append(summary["total_population"])
                trends["urban_population"].append(summary["urban_population"])
                trends["rural_population"].append(summary["rural_population"])
                urban_ratios.append(summary["average_urban_ratio"])

        if len(trends["total_population"]) >= 2:
            first_pop = trends["total_population"][0]
            last_pop = trends["total_population"][-1]
            trends["growth_rate"] = ((last_pop - first_pop) / first_pop) * 100 if first_pop > 0 else 0
        else:
            trends["growth_rate"] = 0

        trends["average_urban_ratio"] = float(np.mean(urban_ratios)) if urban_ratios else 0
        return trends


csv_loader = CSVLoader()
