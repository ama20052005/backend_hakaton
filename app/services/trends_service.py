import numpy as np

from app.models import GrowthDeclineItem, GrowthDeclineResponse
from app.services.data_service import data_service


class TrendsService:
    """Сервис расчета трендов по населению."""

    def _filter_russia(self, df):
        return df[~df["name"].astype(str).str.lower().str.contains("российская феде", na=False)]

    def get_growth_decline(
        self,
        start_year: int,
        end_year: int,
        limit: int = 10,
    ) -> GrowthDeclineResponse:
        start_df = data_service.get_data_for_year(start_year)
        end_df = data_service.get_data_for_year(end_year)

        if start_df is None or end_df is None:
            return GrowthDeclineResponse(
                start_year=start_year,
                end_year=end_year,
                growth=[],
                decline=[],
            )

        filtered_start = self._filter_russia(start_df)
        filtered_end = self._filter_russia(end_df)

        merged = filtered_start[["name", "total_population"]].rename(
            columns={"total_population": "start_population"}
        ).merge(
            filtered_end[["name", "total_population"]].rename(
                columns={"total_population": "end_population"}
            ),
            on="name",
            how="inner",
        )

        if merged.empty:
            return GrowthDeclineResponse(
                start_year=start_year,
                end_year=end_year,
                growth=[],
                decline=[],
            )

        merged["absolute_change"] = merged["end_population"] - merged["start_population"]
        merged["percent_change"] = np.where(
            merged["start_population"] > 0,
            (merged["absolute_change"] / merged["start_population"]) * 100,
            0,
        )

        growth_rows = merged[merged["absolute_change"] > 0].sort_values(
            "absolute_change",
            ascending=False,
        ).head(limit)
        decline_rows = merged[merged["absolute_change"] < 0].sort_values(
            "absolute_change",
            ascending=True,
        ).head(limit)

        return GrowthDeclineResponse(
            start_year=start_year,
            end_year=end_year,
            growth=[self._row_to_item(row) for _, row in growth_rows.iterrows()],
            decline=[self._row_to_item(row) for _, row in decline_rows.iterrows()],
        )

    def _row_to_item(self, row) -> GrowthDeclineItem:
        return GrowthDeclineItem(
            name=str(row["name"]),
            start_population=int(row["start_population"]),
            end_population=int(row["end_population"]),
            absolute_change=int(row["absolute_change"]),
            percent_change=float(row["percent_change"]),
        )


trends_service = TrendsService()
