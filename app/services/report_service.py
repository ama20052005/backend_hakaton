from datetime import datetime
from pathlib import Path
import re
from typing import List
from uuid import uuid4

from fastapi import HTTPException

from app.config import settings
from app.models import (
    ReportFormat,
    ReportGenerationRequest,
    ReportGenerationResponse,
    ReportMetric,
    ReportPayload,
    ReportScope,
    ReportSection,
    ReportTable,
)
from app.services.data_service import data_service
from app.services.llama_service import llama_service
from app.services.report_export_service import report_export_service
from app.services.trends_service import trends_service
from app.utils.formatters import format_number, format_percent, format_signed_number


class ReportService:
    """Собирает аналитическую справку и экспортирует ее в документы."""

    def __init__(self):
        self.reports_dir = Path(settings.REPORTS_DIR)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    async def generate_report(
        self,
        request: ReportGenerationRequest,
        api_prefix: str = settings.API_V1_PREFIX,
    ) -> ReportGenerationResponse:
        payload = await self._build_payload(request)
        report_dir = self.reports_dir / payload.report_id

        try:
            files = report_export_service.export(
                payload=payload,
                output_dir=report_dir,
                report_format=request.format,
                api_prefix=api_prefix,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return ReportGenerationResponse(
            report_id=payload.report_id,
            title=payload.title,
            scope=payload.scope,
            start_year=request.start_year,
            end_year=request.end_year,
            created_at=payload.generated_at,
            files=files,
        )

    def get_report_file_path(self, report_id: str, report_format: ReportFormat) -> Path:
        return self.reports_dir / report_id / f"report_{report_id}.{report_format.value}"

    def _average_annual_delta(
        self,
        series: List,
        attr_name: str,
        recent_years: int | None = None,
    ) -> float:
        if len(series) < 2:
            return 0.0

        if recent_years is None:
            start_item = series[0]
        else:
            window_size = min(len(series), recent_years + 1)
            start_item = series[-window_size]

        end_item = series[-1]
        year_span = end_item.year - start_item.year
        if year_span <= 0:
            return 0.0

        return (getattr(end_item, attr_name) - getattr(start_item, attr_name)) / year_span

    def _format_pp(self, value: float) -> str:
        prefix = "+" if value > 0 else ""
        return f"{prefix}{value:.2f} п.п."

    def _population_change_verb(self, absolute_change: int) -> str:
        if absolute_change > 0:
            return "выросла"
        if absolute_change < 0:
            return "сократилась"
        return "существенно не изменилась"

    def _trend_noun(self, absolute_change: int) -> str:
        if absolute_change > 0:
            return "рост"
        if absolute_change < 0:
            return "снижение"
        return "стабилизация"

    def _build_recent_dynamics_note(
        self,
        overall_annual_change: float,
        recent_annual_change: float,
    ) -> str:
        if abs(overall_annual_change) < 1 and abs(recent_annual_change) < 1:
            return "Динамика последних лет близка к стабилизации."
        if overall_annual_change <= 0 < recent_annual_change:
            return "В последние годы наметилась локальная стабилизация и переход к росту."
        if overall_annual_change >= 0 > recent_annual_change:
            return "В последние годы положительная динамика ослабла и сменилась снижением."
        if abs(overall_annual_change) < 1:
            if recent_annual_change > 0:
                return "В последние годы сформировалась умеренная восходящая динамика."
            return "В последние годы сформировалась умеренная нисходящая динамика."

        ratio = abs(recent_annual_change) / max(abs(overall_annual_change), 1)
        if ratio > 1.15:
            return (
                "В последние годы темп роста ускорился."
                if recent_annual_change > 0
                else "В последние годы темп снижения ускорился."
            )
        if ratio < 0.85:
            return (
                "В последние годы темп роста замедлился."
                if recent_annual_change > 0
                else "В последние годы темп снижения замедлился."
            )
        return "Динамика последних лет в целом соответствует среднему темпу рассматриваемого периода."

    def _build_forecast_point(self, series: List, years_ahead: int) -> dict:
        overall_population_delta = self._average_annual_delta(series, "total_population")
        recent_population_delta = self._average_annual_delta(
            series,
            "total_population",
            recent_years=3,
        )
        overall_ratio_delta = self._average_annual_delta(series, "urban_ratio")
        recent_ratio_delta = self._average_annual_delta(series, "urban_ratio", recent_years=3)

        annual_population_delta = overall_population_delta
        annual_ratio_delta = overall_ratio_delta
        if len(series) >= 4:
            annual_population_delta = (overall_population_delta + recent_population_delta) / 2
            annual_ratio_delta = (overall_ratio_delta + recent_ratio_delta) / 2

        end_item = series[-1]
        population = max(0, round(end_item.total_population + annual_population_delta * years_ahead))
        urban_ratio = min(1.0, max(0.0, end_item.urban_ratio + annual_ratio_delta * years_ahead))
        absolute_change = population - end_item.total_population
        percent_change = (
            (absolute_change / end_item.total_population) * 100
            if end_item.total_population > 0
            else 0
        )

        return {
            "years_ahead": years_ahead,
            "forecast_year": end_item.year + years_ahead,
            "population": population,
            "absolute_change": absolute_change,
            "percent_change": percent_change,
            "urban_ratio": urban_ratio,
        }

    def _build_forecast_table(
        self,
        forecast_five_years: dict,
        forecast_ten_years: dict,
        baseline_year: int,
    ) -> ReportTable:
        return ReportTable(
            title="Оценка при сохранении текущей траектории",
            columns=[
                "Горизонт",
                "Прогнозный год",
                "Население",
                f"Изменение к {baseline_year} году",
                "% изменение",
                "Доля городского населения",
            ],
            rows=[
                [
                    "Через 5 лет",
                    str(forecast_five_years["forecast_year"]),
                    format_number(forecast_five_years["population"]),
                    format_signed_number(forecast_five_years["absolute_change"]),
                    format_percent(forecast_five_years["percent_change"]),
                    format_percent(forecast_five_years["urban_ratio"] * 100),
                ],
                [
                    "Через 10 лет",
                    str(forecast_ten_years["forecast_year"]),
                    format_number(forecast_ten_years["population"]),
                    format_signed_number(forecast_ten_years["absolute_change"]),
                    format_percent(forecast_ten_years["percent_change"]),
                    format_percent(forecast_ten_years["urban_ratio"] * 100),
                ],
            ],
        )

    def _build_factor_paragraph(
        self,
        absolute_change: int,
        urban_ratio_change_pp: float,
        urban_change: int,
        rural_change: int,
    ) -> str:
        if absolute_change < 0 and urban_ratio_change_pp > 0.3:
            return (
                "Сочетание общей убыли населения с ростом доли городских жителей может указывать "
                "на концентрацию населения в крупных центрах, миграционный отток из малых и "
                "сельских населенных пунктов и различия в доступности рабочих мест и базовых услуг."
            )
        if absolute_change > 0 and urban_ratio_change_pp > 0.3:
            return (
                "Рост численности населения вместе с увеличением доли городских жителей указывает "
                "на усиление агломерационного эффекта; возможными факторами являются миграционная "
                "привлекательность крупных центров, развитие жилищного строительства и расширение "
                "пригородных зон."
            )
        if absolute_change < 0 and urban_change < 0 and rural_change < 0:
            return (
                "Одновременное снижение городского и сельского населения говорит о более широком "
                "сжатии демографической базы; возможными факторами могут быть естественная убыль, "
                "недостаточный миграционный приток и ограниченная устойчивость локальных рынков труда."
            )
        if rural_change < 0 <= urban_change:
            return (
                "При сокращении сельского населения и более устойчивой динамике городских территорий "
                "можно предполагать внутреннюю концентрацию жителей вокруг опорных центров и снижение "
                "привлекательности периферийных поселений."
            )
        if absolute_change > 0:
            return (
                "Текущая динамика указывает на относительно благоприятную демографическую траекторию; "
                "возможными факторами влияния могут быть миграционный приток, расширение занятости "
                "и рост привлекательности территории для проживания."
            )
        return (
            "Выраженных структурных сдвигов по одной только численности населения недостаточно для "
            "однозначного вывода; возможные факторы требуют дополнительной проверки на данных о "
            "миграции, рождаемости, смертности и занятости."
        )

    def _build_recommendations(
        self,
        absolute_change: int,
        urban_ratio_change_pp: float,
        rural_change: int,
    ) -> List[str]:
        recommendations: List[str] = []

        if absolute_change < 0:
            recommendations.append(
                "Сфокусировать социальную политику на удержании населения: доступности рабочих мест, "
                "поддержке молодых семей, первичного здравоохранения и базовых социальных услуг."
            )
        else:
            recommendations.append(
                "Планирование социальной инфраструктуры следует увязать с зонами роста населения, "
                "чтобы заранее расширять мощности школ, детских садов, поликлиник и жилья."
            )

        if rural_change < 0:
            recommendations.append(
                "Для сельской сети целесообразно развивать опорные населенные пункты, транспортную "
                "связность, мобильные социальные сервисы и доступность первичных услуг."
            )
        else:
            recommendations.append(
                "В территориальном планировании важно поддерживать сбалансированную сеть услуг между "
                "городскими и сельскими территориями, не допуская сверхконцентрации нагрузки."
            )

        if urban_ratio_change_pp > 0.3:
            recommendations.append(
                "Рост доли городского населения требует резервирования мощностей общественного "
                "транспорта, инженерной инфраструктуры и земель под развитие городских и пригородных зон."
            )
        else:
            recommendations.append(
                "При относительно стабильной структуре расселения приоритетом должно оставаться "
                "поддержание качества среды в существующей сети населенных пунктов без избыточного распыления инвестиций."
            )

        recommendations.append(
            "Для уточнения мер рекомендуется дополнить мониторинг данными о миграции, рождаемости, "
            "смертности и занятости, поскольку текущая прогнозная оценка построена на динамике численности населения."
        )

        return [f"{index}. {text}" for index, text in enumerate(recommendations, start=1)]

    def _summarize_top_names(self, items: List, limit: int = 3) -> str:
        names = [item.name for item in items[:limit]]
        return ", ".join(names) if names else "данных недостаточно"

    async def _build_payload(self, request: ReportGenerationRequest) -> ReportPayload:
        if request.scope == ReportScope.REGION:
            return await self._build_region_payload(request)
        return await self._build_russia_payload(request)

    async def _build_russia_payload(self, request: ReportGenerationRequest) -> ReportPayload:
        years = list(range(request.start_year, request.end_year + 1))
        yearly_stats = [data_service.get_year_statistics(year) for year in years]
        yearly_stats = [item for item in yearly_stats if item is not None]
        if len(yearly_stats) != len(years):
            raise HTTPException(
                status_code=404,
                detail="No complete data found for the selected period",
            )

        start_stat = yearly_stats[0]
        end_stat = yearly_stats[-1]
        absolute_change = end_stat.total_population - start_stat.total_population
        percent_change = (
            (absolute_change / start_stat.total_population) * 100
            if start_stat.total_population > 0
            else 0
        )
        urban_change = end_stat.urban_population - start_stat.urban_population
        rural_change = end_stat.rural_population - start_stat.rural_population
        urban_ratio_change_pp = (end_stat.urban_ratio - start_stat.urban_ratio) * 100
        average_annual_change = self._average_annual_delta(yearly_stats, "total_population")
        recent_annual_change = self._average_annual_delta(
            yearly_stats,
            "total_population",
            recent_years=3,
        )
        recent_note = self._build_recent_dynamics_note(
            average_annual_change,
            recent_annual_change,
        )
        forecast_five_years = self._build_forecast_point(yearly_stats, 5)
        forecast_ten_years = self._build_forecast_point(yearly_stats, 10)

        growth_decline = trends_service.get_growth_decline(
            start_year=request.start_year,
            end_year=request.end_year,
            limit=10,
        )
        top_regions = sorted(
            data_service.get_regions(request.end_year),
            key=lambda item: item.total_population,
            reverse=True,
        )[:10]

        ai_summary = await self._generate_ai_summary(
            request=request,
            scope_label="Россия",
            yearly_rows=[
                (
                    stat.year,
                    stat.total_population,
                    stat.urban_population,
                    stat.rural_population,
                    stat.urban_ratio,
                )
                for stat in yearly_stats
            ],
            comparison_rows=[
                (
                    item.name,
                    item.start_population,
                    item.end_population,
                    item.absolute_change,
                    item.percent_change,
                )
                for item in growth_decline.growth[:5] + growth_decline.decline[:5]
            ],
            fallback=(
                f"За период {request.start_year}-{request.end_year} гг. численность населения России "
                f"изменилась на {format_signed_number(absolute_change)} человек "
                f"({format_percent(percent_change)}). На конец периода доля городского населения "
                f"составила {format_percent(end_stat.urban_ratio * 100)}."
            ),
        )

        sections = [
            ReportSection(
                heading="Краткое резюме динамики населения",
                paragraphs=[
                    (
                        f"За {request.start_year}-{request.end_year} гг. численность населения России "
                        f"{self._population_change_verb(absolute_change)} с "
                        f"{format_number(start_stat.total_population)} до "
                        f"{format_number(end_stat.total_population)} человек, что соответствует "
                        f"{format_signed_number(absolute_change)} человек "
                        f"({format_percent(percent_change)}). Среднегодовое изменение составило "
                        f"{format_signed_number(round(average_annual_change))} человек."
                    ),
                    (
                        f"На {request.end_year} год доля городского населения составляет "
                        f"{format_percent(end_stat.urban_ratio * 100)}; изменение структуры расселения "
                        f"за период оценивается в {self._format_pp(urban_ratio_change_pp)}. "
                        f"Городское население изменилось на {format_signed_number(urban_change)} человек, "
                        f"сельское — на {format_signed_number(rural_change)} человек."
                    ),
                    recent_note,
                ],
            ),
            ReportSection(
                heading="Выявленные демографические тенденции и возможные факторы влияния",
                paragraphs=[
                    (
                        f"Базовый тренд периода — {self._trend_noun(absolute_change)} общей численности "
                        f"населения при {'росте доли' if urban_ratio_change_pp > 0 else 'снижении доли' if urban_ratio_change_pp < 0 else 'стабильной доле'} "
                        f"городских жителей."
                    ),
                    (
                        f"Наиболее заметная пространственная дифференциация наблюдается между регионами: "
                        f"лидерами прироста за период стали {self._summarize_top_names(growth_decline.growth)}, "
                        f"а наиболее выраженное снижение зафиксировано в {self._summarize_top_names(growth_decline.decline)}."
                    ),
                    self._build_factor_paragraph(
                        absolute_change,
                        urban_ratio_change_pp,
                        urban_change,
                        rural_change,
                    ),
                ],
                tables=[
                    ReportTable(
                        title="Лидеры роста",
                        columns=[
                            "Регион",
                            f"Население {request.start_year}",
                            f"Население {request.end_year}",
                            "Абс. изменение",
                            "% изменение",
                        ],
                        rows=[
                            [
                                item.name,
                                format_number(item.start_population),
                                format_number(item.end_population),
                                format_signed_number(item.absolute_change),
                                format_percent(item.percent_change),
                            ]
                            for item in growth_decline.growth
                        ]
                        or [["Нет данных", "-", "-", "-", "-"]],
                    ),
                    ReportTable(
                        title="Лидеры снижения",
                        columns=[
                            "Регион",
                            f"Население {request.start_year}",
                            f"Население {request.end_year}",
                            "Абс. изменение",
                            "% изменение",
                        ],
                        rows=[
                            [
                                item.name,
                                format_number(item.start_population),
                                format_number(item.end_population),
                                format_signed_number(item.absolute_change),
                                format_percent(item.percent_change),
                            ]
                            for item in growth_decline.decline
                        ]
                        or [["Нет данных", "-", "-", "-", "-"]],
                    ),
                ],
            ),
            ReportSection(
                heading="Прогнозная оценка на 5-10 лет",
                paragraphs=[
                    (
                        "Прогноз носит ориентировочный характер и построен методом линейной экстраполяции "
                        "на основе средней и недавней годовой динамики численности населения."
                    ),
                    (
                        f"При сохранении текущей траектории численность населения России может составить "
                        f"около {format_number(forecast_five_years['population'])} человек к "
                        f"{forecast_five_years['forecast_year']} году и "
                        f"{format_number(forecast_ten_years['population'])} человек к "
                        f"{forecast_ten_years['forecast_year']} году."
                    ),
                ],
                tables=[
                    self._build_forecast_table(
                        forecast_five_years,
                        forecast_ten_years,
                        request.end_year,
                    )
                ],
            ),
            ReportSection(
                heading="Рекомендации по социальной политике и территориальному планированию",
                paragraphs=self._build_recommendations(
                    absolute_change,
                    urban_ratio_change_pp,
                    rural_change,
                ),
            ),
            ReportSection(
                heading="Статистические таблицы",
                tables=[
                    ReportTable(
                        title="Динамика по годам",
                        columns=[
                            "Год",
                            "Все население",
                            "Городское",
                            "Сельское",
                            "Доля городского населения",
                        ],
                        rows=[
                            [
                                str(stat.year),
                                format_number(stat.total_population),
                                format_number(stat.urban_population),
                                format_number(stat.rural_population),
                                format_percent(stat.urban_ratio * 100),
                            ]
                            for stat in yearly_stats
                        ],
                    ),
                    ReportTable(
                        title=f"Топ-10 регионов по населению за {request.end_year} год",
                        columns=["Регион", "Население", "Доля городского населения"],
                        rows=[
                            [
                                region.name,
                                format_number(region.total_population),
                                format_percent(region.urban_ratio * 100),
                            ]
                            for region in top_regions
                        ],
                    ),
                ],
            ),
        ]

        if request.include_ai_summary:
            sections.append(
                ReportSection(
                    heading="Дополнительное аналитическое заключение",
                    paragraphs=[ai_summary],
                )
            )

        return ReportPayload(
            report_id=uuid4().hex[:12],
            title="Аналитическая справка по демографическим данным России",
            subtitle=f"Период анализа: {request.start_year}-{request.end_year} гг.",
            generated_at=datetime.now(),
            scope=ReportScope.RUSSIA,
            parameters={
                "Охват": "Россия",
                "Период": f"{request.start_year}-{request.end_year}",
                "Источник": "CSV-файлы data/yearly",
                "AI-блок": "включен" if request.include_ai_summary else "отключен",
            },
            summary_metrics=[
                ReportMetric(
                    label=f"Население на {request.start_year} год",
                    value=format_number(start_stat.total_population),
                ),
                ReportMetric(
                    label=f"Население на {request.end_year} год",
                    value=format_number(end_stat.total_population),
                ),
                ReportMetric(
                    label="Абсолютное изменение",
                    value=format_signed_number(absolute_change),
                ),
                ReportMetric(
                    label="Изменение за период",
                    value=format_percent(percent_change),
                ),
                ReportMetric(
                    label="Среднегодовое изменение",
                    value=format_signed_number(round(average_annual_change)),
                ),
                ReportMetric(
                    label=f"Прогноз населения на {forecast_five_years['forecast_year']} год",
                    value=format_number(forecast_five_years["population"]),
                ),
                ReportMetric(
                    label=f"Доля городского населения на {request.end_year} год",
                    value=format_percent(end_stat.urban_ratio * 100),
                ),
            ],
            sections=sections,
        )

    async def _build_region_payload(self, request: ReportGenerationRequest) -> ReportPayload:
        years = list(range(request.start_year, request.end_year + 1))
        region_series = data_service.get_population_series(request.region_name or "", years)
        if (
            not region_series
            or region_series[0].year != request.start_year
            or region_series[-1].year != request.end_year
        ):
            raise HTTPException(status_code=404, detail="Region not found for the selected period")

        russia_series = [data_service.get_year_statistics(year) for year in years]
        russia_series = [item for item in russia_series if item is not None]
        if len(russia_series) != len(years):
            raise HTTPException(
                status_code=404,
                detail="No complete national data found for the selected period",
            )

        region_name = region_series[-1].name
        start_stat = region_series[0]
        end_stat = region_series[-1]
        absolute_change = end_stat.total_population - start_stat.total_population
        percent_change = (
            (absolute_change / start_stat.total_population) * 100
            if start_stat.total_population > 0
            else 0
        )
        urban_change = end_stat.urban_population - start_stat.urban_population
        rural_change = end_stat.rural_population - start_stat.rural_population
        urban_ratio_change_pp = (end_stat.urban_ratio - start_stat.urban_ratio) * 100
        average_annual_change = self._average_annual_delta(region_series, "total_population")
        recent_annual_change = self._average_annual_delta(
            region_series,
            "total_population",
            recent_years=3,
        )
        recent_note = self._build_recent_dynamics_note(
            average_annual_change,
            recent_annual_change,
        )
        forecast_five_years = self._build_forecast_point(region_series, 5)
        forecast_ten_years = self._build_forecast_point(region_series, 10)

        russia_start = russia_series[0]
        russia_end = russia_series[-1]
        russia_absolute_change = russia_end.total_population - russia_start.total_population
        russia_percent_change = (
            (russia_absolute_change / russia_start.total_population) * 100
            if russia_start.total_population > 0
            else 0
        )
        region_vs_russia_delta = percent_change - russia_percent_change

        end_year_regions = sorted(
            data_service.get_regions(request.end_year),
            key=lambda item: item.total_population,
            reverse=True,
        )
        region_rank = next(
            (
                index
                for index, region in enumerate(end_year_regions, start=1)
                if region.name.lower() == region_name.lower()
            ),
            None,
        )
        total_russia_end = sum(item.total_population for item in end_year_regions)
        region_share = (
            (end_stat.total_population / total_russia_end) * 100 if total_russia_end > 0 else 0
        )
        top_peers = end_year_regions[:10]

        ai_summary = await self._generate_ai_summary(
            request=request,
            scope_label=region_name,
            yearly_rows=[
                (
                    item.year,
                    item.total_population,
                    item.urban_population,
                    item.rural_population,
                    item.urban_ratio,
                )
                for item in region_series
            ],
            comparison_rows=[
                (peer.name, peer.total_population, peer.urban_ratio)
                for peer in top_peers[:5]
            ],
            fallback=(
                f"За период {request.start_year}-{request.end_year} гг. численность населения региона "
                f"{region_name} изменилась на {format_signed_number(absolute_change)} человек "
                f"({format_percent(percent_change)}). На {request.end_year} год доля городского населения "
                f"составляет {format_percent(end_stat.urban_ratio * 100)}."
            ),
        )

        if abs(region_vs_russia_delta) < 1:
            comparison_text = "Динамика региона близка к общероссийской."
        elif region_vs_russia_delta > 0:
            comparison_text = (
                f"Динамика региона лучше общероссийской на {abs(region_vs_russia_delta):.2f} п.п."
            )
        else:
            comparison_text = (
                f"Динамика региона слабее общероссийской на {abs(region_vs_russia_delta):.2f} п.п."
            )

        rank_text = (
            f"Регион занимает {region_rank}-е место по численности населения в {request.end_year} году."
            if region_rank is not None
            else "Позиция региона в ранжировании не определена."
        )

        sections = [
            ReportSection(
                heading="Краткое резюме динамики населения",
                paragraphs=[
                    (
                        f"За {request.start_year}-{request.end_year} гг. численность населения региона "
                        f"{region_name} {self._population_change_verb(absolute_change)} с "
                        f"{format_number(start_stat.total_population)} до "
                        f"{format_number(end_stat.total_population)} человек, что соответствует "
                        f"{format_signed_number(absolute_change)} человек "
                        f"({format_percent(percent_change)}). Среднегодовое изменение составило "
                        f"{format_signed_number(round(average_annual_change))} человек."
                    ),
                    (
                        f"На {request.end_year} год доля городского населения составляет "
                        f"{format_percent(end_stat.urban_ratio * 100)}; изменение за период — "
                        f"{self._format_pp(urban_ratio_change_pp)}. Доля региона в населении России "
                        f"оценивается в {format_percent(region_share)}. {rank_text}"
                    ),
                    recent_note,
                ],
            ),
            ReportSection(
                heading="Выявленные демографические тенденции и возможные факторы влияния",
                paragraphs=[
                    (
                        f"Базовый тренд периода — {self._trend_noun(absolute_change)} численности населения "
                        f"региона при {'росте доли' if urban_ratio_change_pp > 0 else 'снижении доли' if urban_ratio_change_pp < 0 else 'стабильной доле'} "
                        f"городских жителей. {comparison_text}"
                    ),
                    (
                        f"Городское население изменилось на {format_signed_number(urban_change)} человек, "
                        f"сельское — на {format_signed_number(rural_change)} человек. Это позволяет оценивать "
                        f"изменение структуры расселения без выхода за рамки имеющихся данных."
                    ),
                    self._build_factor_paragraph(
                        absolute_change,
                        urban_ratio_change_pp,
                        urban_change,
                        rural_change,
                    ),
                ],
            ),
            ReportSection(
                heading="Прогнозная оценка на 5-10 лет",
                paragraphs=[
                    (
                        "Прогноз носит ориентировочный характер и построен методом линейной экстраполяции "
                        "на основе средней и недавней годовой динамики численности населения."
                    ),
                    (
                        f"При сохранении текущей траектории численность населения региона {region_name} "
                        f"может составить около {format_number(forecast_five_years['population'])} человек к "
                        f"{forecast_five_years['forecast_year']} году и "
                        f"{format_number(forecast_ten_years['population'])} человек к "
                        f"{forecast_ten_years['forecast_year']} году."
                    ),
                ],
                tables=[
                    self._build_forecast_table(
                        forecast_five_years,
                        forecast_ten_years,
                        request.end_year,
                    )
                ],
            ),
            ReportSection(
                heading="Рекомендации по социальной политике и территориальному планированию",
                paragraphs=self._build_recommendations(
                    absolute_change,
                    urban_ratio_change_pp,
                    rural_change,
                ),
            ),
            ReportSection(
                heading="Статистические таблицы",
                tables=[
                    ReportTable(
                        title=f"Динамика региона {region_name}",
                        columns=[
                            "Год",
                            "Все население",
                            "Городское",
                            "Сельское",
                            "Доля городского населения",
                        ],
                        rows=[
                            [
                                str(item.year),
                                format_number(item.total_population),
                                format_number(item.urban_population),
                                format_number(item.rural_population),
                                format_percent(item.urban_ratio * 100),
                            ]
                            for item in region_series
                        ],
                    ),
                    ReportTable(
                        title=f"Топ-10 регионов по населению за {request.end_year} год",
                        columns=["Место", "Регион", "Население", "Доля городского населения"],
                        rows=[
                            [
                                str(index),
                                peer.name,
                                format_number(peer.total_population),
                                format_percent(peer.urban_ratio * 100),
                            ]
                            for index, peer in enumerate(top_peers, start=1)
                        ],
                    ),
                ],
            ),
        ]

        if request.include_ai_summary:
            sections.append(
                ReportSection(
                    heading="Дополнительное аналитическое заключение",
                    paragraphs=[ai_summary],
                )
            )

        return ReportPayload(
            report_id=uuid4().hex[:12],
            title=f"Аналитическая справка по региону {region_name}",
            subtitle=f"Период анализа: {request.start_year}-{request.end_year} гг.",
            generated_at=datetime.now(),
            scope=ReportScope.REGION,
            parameters={
                "Охват": region_name,
                "Период": f"{request.start_year}-{request.end_year}",
                "Источник": "CSV-файлы data/yearly",
                "AI-блок": "включен" if request.include_ai_summary else "отключен",
            },
            summary_metrics=[
                ReportMetric(
                    label=f"Население на {request.start_year} год",
                    value=format_number(start_stat.total_population),
                ),
                ReportMetric(
                    label=f"Население на {request.end_year} год",
                    value=format_number(end_stat.total_population),
                ),
                ReportMetric(
                    label="Абсолютное изменение",
                    value=format_signed_number(absolute_change),
                ),
                ReportMetric(
                    label="Изменение за период",
                    value=format_percent(percent_change),
                ),
                ReportMetric(
                    label="Среднегодовое изменение",
                    value=format_signed_number(round(average_annual_change)),
                ),
                ReportMetric(
                    label=f"Прогноз населения на {forecast_five_years['forecast_year']} год",
                    value=format_number(forecast_five_years["population"]),
                ),
                ReportMetric(
                    label=f"Доля населения России на {request.end_year} год",
                    value=format_percent(region_share),
                ),
            ],
            sections=sections,
        )

    async def _generate_ai_summary(
        self,
        request: ReportGenerationRequest,
        scope_label: str,
        yearly_rows: List[tuple],
        comparison_rows: List[tuple],
        fallback: str,
    ) -> str:
        if not request.include_ai_summary:
            return fallback

        year_lines = []
        for row in yearly_rows:
            year, total, urban, rural, urban_ratio = row
            year_lines.append(
                f"{year}: население={total}, городское={urban}, сельское={rural}, урбанизация={urban_ratio:.4f}"
            )

        comparison_lines = [", ".join(str(value) for value in row) for row in comparison_rows]
        focus = request.focus_prompt or "Сделай акцент на ключевых изменениях и практических выводах."
        prompt = "\n".join(
            [
                "Ты готовишь краткое аналитическое заключение для официальной демографической справки.",
                "Ответ пиши строго на русском языке, без английских слов, транслита и Markdown.",
                f"Охват: {scope_label}",
                f"Период: {request.start_year}-{request.end_year}",
                "Используй только данные из контекста, не придумывай новых фактов.",
                "Сформулируй 2 коротких абзаца официально-деловым стилем.",
                "Не добавляй регионы и показатели, которых нет в сравнительных данных.",
                "Если данных недостаточно для вывода, прямо укажи это.",
                focus,
                "",
                "Динамика по годам:",
                *year_lines,
                "",
                "Сравнительные данные:",
                *comparison_lines,
                "",
                "Заключение:",
            ]
        )
        result = await llama_service.generate(
            prompt=prompt,
            model=request.model,
            temperature=0.2,
            max_tokens=450,
            year=request.end_year,
            use_cache=True,
        )
        response = (result.get("response") or "").strip()
        if not response:
            return fallback

        lower_response = response.lower()
        if "ошибка" in lower_response or "превышено время ожидания" in lower_response:
            return fallback

        # Для официальной справки не пропускаем ответы с заметной примесью английского.
        latin_words = re.findall(r"[A-Za-z]{3,}", response)
        if len(latin_words) >= 3:
            return fallback

        return response


report_service = ReportService()
