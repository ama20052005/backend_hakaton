# app/services/data_service.py
from typing import Dict, List, Optional

import pandas as pd

from app.models import MunicipalityData, YearlyStatistic
from app.utils.csv_loader import csv_loader


class DataService:
    """Сервис для работы с демографическими данными."""

    def __init__(self):
        self.loader = csv_loader

    def get_data_for_year(self, year: int) -> Optional[pd.DataFrame]:
        """Получает DataFrame за указанный год."""

        return self.loader.load_year(year)

    def _row_to_model(self, row: pd.Series, year: int) -> MunicipalityData:
        return MunicipalityData(
            code=str(row["code"]),
            name=str(row["name"]),
            total_population=int(row["total_population"]),
            urban_population=int(row["urban_population"]),
            rural_population=int(row["rural_population"]),
            urban_ratio=float(row["urban_ratio"]),
            year=year,
        )

    def get_municipality(self, code: str, year: int = 2024) -> Optional[MunicipalityData]:
        """Получает данные территориальной единицы по коду или имени."""

        df = self.loader.load_year(year)
        if df is None:
            return None

        code_str = str(code).strip()
        row = df[df["code"].astype(str) == code_str]
        if row.empty:
            row = df[df["name"].str.lower() == code_str.lower()]
        if row.empty:
            return None

        return self._row_to_model(row.iloc[0], year)

    def get_region_by_name(self, name: str, year: int = 2024) -> Optional[MunicipalityData]:
        """Находит регион по точному названию с учетом регистра."""

        df = self.loader.load_year(year)
        if df is None:
            return None

        normalized = name.strip().lower()
        matches = df[df["name"].str.lower() == normalized]
        if matches.empty:
            return None

        return self._row_to_model(matches.iloc[0], year)

    def search_municipality(
        self,
        query: str,
        year: int = 2024,
        limit: int = 10,
    ) -> List[MunicipalityData]:
        """Ищет записи по названию."""

        df = self.loader.load_year(year)
        if df is None:
            return []

        mask = df["name"].str.contains(query, case=False, na=False)
        results = df[mask].head(limit)
        return [self._row_to_model(row, year) for _, row in results.iterrows()]

    def get_top_cities(self, year: int = 2024, n: int = 10) -> List[MunicipalityData]:
        """Возвращает крупнейшие записи по населению."""

        df = self.loader.load_year(year)
        if df is None:
            return []

        top_df = df.nlargest(n, "total_population")
        return [self._row_to_model(row, year) for _, row in top_df.iterrows()]

    def get_regions(self, year: int = 2024) -> List[MunicipalityData]:
        """Возвращает список регионов за год.

        Текущий датасет уже находится на региональном уровне, поэтому
        дополнительных фильтров по иерархии не требуется.
        """

        df = self.loader.load_year(year)
        if df is None:
            return []

        return [self._row_to_model(row, year) for _, row in df.iterrows()]

    def get_population_series(self, name: str, years: List[int]) -> List[MunicipalityData]:
        """Возвращает временной ряд по региону за указанные годы."""

        series: List[MunicipalityData] = []
        normalized = name.strip().lower()

        for year in sorted(years):
            df = self.loader.load_year(year)
            if df is None:
                continue

            matches = df[df["name"].str.lower() == normalized]
            if matches.empty:
                continue
            series.append(self._row_to_model(matches.iloc[0], year))

        return series

    def get_year_statistics(self, year: int) -> Optional[YearlyStatistic]:
        """Получает общую статистику за год."""

        summary = self.loader.get_year_summary(year)
        if summary is None:
            return None

        return YearlyStatistic(
            year=summary["year"],
            total_population=summary["total_population"],
            urban_population=summary["urban_population"],
            rural_population=summary["rural_population"],
            urban_ratio=summary["average_urban_ratio"],
            number_of_municipalities=summary["number_of_municipalities"],
        )

    def get_available_years(self) -> List[int]:
        """Получает список доступных годов."""

        return self.loader.get_available_years()

    def get_yearly_trends(self, years: Optional[List[int]] = None) -> Dict:
        """Получает тренды за указанные годы."""

        if years is None:
            years = self.get_available_years()

        return self.loader.get_trends(years)


data_service = DataService()
