import { useDeferredValue, useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import LanguageToggle from "./LanguageToggle";
import {
  fetchRegions,
  fetchTerritorySeries,
  fetchTrends,
  fetchYears,
  type MunicipalityData,
} from "../lib/api";
import {
  formatCompactPopulation,
  formatInteger,
  formatPercent,
  formatSignedInteger,
} from "../lib/format";
import { useLanguage, type AppLanguage } from "../lib/language";
import { buildSeriesFromTrend, buildYearRange, toSeriesPoint, type SeriesPoint } from "../lib/insights";

type TerritoryType =
  | "all"
  | "republic"
  | "oblast"
  | "krai"
  | "okrug"
  | "city"
  | "other";

interface ComparisonRow {
  code: string;
  name: string;
  type: TerritoryType;
  startPopulation: number;
  endPopulation: number;
  urbanRatio: number;
  absoluteChange: number;
  percentChange: number;
}

interface ForecastPoint {
  year: number;
  population: number;
  percentChange: number;
}

const RUSSIA_ID = "russia";

const analyticsCopy = {
  ru: {
    sectionLabel: "Аналитика населения",
    heading: "Численность, динамика и территориальная структура",
    description:
      "Рабочий экран для анализа населения по субъектам РФ, изменениям за период и сравнительному срезу по текущему набору данных.",
    territory: "Субъект РФ",
    territoryPlaceholder: "Россия или название субъекта",
    territoryHint: "Выбранный субъект сразу связывает графики, тепловую карту и переход к отчету.",
    type: "Группа субъектов",
    start: "Начало периода",
    end: "Конец периода",
    report: "Генерация отчета",
    overview: "Обзор",
    allRussia: "Российская Федерация",
    loading: "Обновляю данные",
    noRows: "Нет совпадений",
    selectedPeriod: "Период анализа",
    selectedType: "Срез сравнения",
    focusContext: "Активный фокус",
    reportSync: "Справка и выгрузка",
    reportSyncTitle: "Текущий контекст перейдет в отчет",
    reportSyncText:
      "Период, выбранный субъект и сравнительный срез переносятся в форму подготовки отчета.",
    reportSyncAction: "Открыть отчет",
    allSubjects: "Все субъекты",
    metrics: {
      population: "Население на конец периода",
      change: "Изменение за период",
      annual: "Среднегодовое изменение",
      urban: "Городское население",
      coverage: "Территорий в выборке",
    },
    mainChartLabel: "Основной ряд",
    mainChartTitle: "Численность населения по выбранному периоду",
    mainChartText:
      "Столбцы показывают городское и сельское население, линия поверх фиксирует совокупную численность.",
    totalPopulation: "Все население",
    urbanPopulation: "Городское",
    ruralPopulation: "Сельское",
    populationUnit: "чел.",
    changeChartLabel: "Год к году",
    changeChartTitle: "Изменение численности в процентах",
    changeChartText: "Положительные значения выделены акцентом, отрицательные — тёплым тоном.",
    indicatorsLabel: "Ключевые демографические показатели",
    indicatorsTitle: "Слой коэффициентов",
    indicatorsNote:
      "Текущий набор данных содержит численность и структуру расселения. Рождаемость, смертность, естественный прирост и миграция будут доступны после подключения расширенной статистической выгрузки.",
    unavailable: "нет данных",
    pending: "ожидает загрузки",
    growthLabel: "Таблица роста и снижения",
    growthTitle: "Территории с максимальной динамикой",
    growth: "Рост",
    decline: "Снижение",
    heatmapLabel: "Тепловая карта",
    heatmapTitle: "Матрица субъектов по численности населения",
    heatmapText:
      "Ровная сетка показывает текущую группу субъектов. Чем насыщеннее ячейка, тем выше население на конец периода.",
    heatScaleLow: "Ниже",
    heatScaleHigh: "Выше",
    registerLabel: "Сводная таблица",
    registerTitle: "Территориальный реестр",
    registerText:
      "Таблица показывает текущую численность, изменение за период и долю городского населения для выбранного типа территорий.",
    territoryColumn: "Территория",
    typeColumn: "Группа",
    endPopulationColumn: "Население",
    changeColumn: "Изменение",
    urbanShareColumn: "Городское население",
    birthRate: "Коэффициент рождаемости",
    deathRate: "Коэффициент смертности",
    naturalIncrease: "Естественный прирост",
    migration: "Миграция",
    notAvailable: "не загружено",
    searchRussia: "Россия",
  },
  en: {
    sectionLabel: "Population analytics",
    heading: "Population size, trajectory, and territorial structure",
    description:
      "Operational screen for reviewing Russian regions, period changes, and the comparative layer built from the current dataset.",
    territory: "Region",
    territoryPlaceholder: "Russia or region name",
    territoryHint: "The selected region immediately drives the charts, heat map, and report handoff.",
    type: "Region group",
    start: "Start year",
    end: "End year",
    report: "Report generation",
    overview: "Overview",
    allRussia: "Russian Federation",
    loading: "Refreshing data",
    noRows: "No matches",
    selectedPeriod: "Analysis period",
    selectedType: "Comparison slice",
    focusContext: "Active context",
    reportSync: "Report and export",
    reportSyncTitle: "The current context will carry into the report",
    reportSyncText:
      "The selected period, region, and comparison slice are transferred into the export form.",
    reportSyncAction: "Open report",
    allSubjects: "All regions",
    metrics: {
      population: "Population at end of period",
      change: "Change over period",
      annual: "Average annual change",
      urban: "Urban population",
      coverage: "Territories in scope",
    },
    mainChartLabel: "Core series",
    mainChartTitle: "Population across the selected period",
    mainChartText:
      "Bars show urban and rural population, while the line marks the total population level.",
    totalPopulation: "Total population",
    urbanPopulation: "Urban",
    ruralPopulation: "Rural",
    populationUnit: "people",
    changeChartLabel: "Year over year",
    changeChartTitle: "Population change in percent",
    changeChartText: "Positive movement uses the accent color, negative movement shifts to a warmer tone.",
    indicatorsLabel: "Key demographic indicators",
    indicatorsTitle: "Vital statistics layer",
    indicatorsNote:
      "The current dataset contains population totals and settlement structure only. Birth rate, death rate, natural increase, and migration can be shown once the extended statistical extract is connected.",
    unavailable: "no data",
    pending: "pending",
    growthLabel: "Growth and decline table",
    growthTitle: "Territories with the strongest movement",
    growth: "Growth",
    decline: "Decline",
    heatmapLabel: "Heat map",
    heatmapTitle: "Regional population matrix",
    heatmapText:
      "A clean grid shows the current region group. Darker tiles indicate higher end-period population.",
    heatScaleLow: "Lower",
    heatScaleHigh: "Higher",
    registerLabel: "Territory register",
    registerTitle: "Comparative territory table",
    registerText:
      "The table shows current population, period change, and urban share for the selected territory type.",
    territoryColumn: "Territory",
    typeColumn: "Group",
    endPopulationColumn: "Population",
    changeColumn: "Change",
    urbanShareColumn: "Urban share",
    birthRate: "Birth rate",
    deathRate: "Death rate",
    naturalIncrease: "Natural increase",
    migration: "Migration",
    notAvailable: "not loaded",
    searchRussia: "Russia",
  },
} as const;

function detectTerritoryType(name: string): TerritoryType {
  const lowerName = name.toLowerCase();

  if (lowerName.includes("республика") || lowerName.includes("republic")) {
    return "republic";
  }
  if (lowerName.includes("область") || lowerName.includes("oblast")) {
    return "oblast";
  }
  if (lowerName.includes("край") || lowerName.includes("krai")) {
    return "krai";
  }
  if (
    lowerName.includes("округ") ||
    lowerName.includes("autonomous okrug") ||
    lowerName.includes("автономная область")
  ) {
    return "okrug";
  }
  if (
    lowerName.includes("москва") ||
    lowerName.includes("санкт-петербург") ||
    lowerName.includes("севастополь")
  ) {
    return "city";
  }

  return "other";
}

function getTypeLabel(type: TerritoryType, language: AppLanguage) {
  const labels = {
    ru: {
      all: "Все",
      republic: "Республика",
      oblast: "Область",
      krai: "Край",
      okrug: "Округ",
      city: "Город федерального значения",
      other: "Другое",
    },
    en: {
      all: "All",
      republic: "Republic",
      oblast: "Oblast",
      krai: "Krai",
      okrug: "Okrug",
      city: "Federal city",
      other: "Other",
    },
  } as const;

  return labels[language][type];
}

function getHeatmapTypeLabel(type: TerritoryType, language: AppLanguage) {
  const labels = {
    ru: {
      all: "Все",
      republic: "Респ.",
      oblast: "Обл.",
      krai: "Край",
      okrug: "Окр.",
      city: "ГФЗ",
      other: "Проч.",
    },
    en: {
      all: "All",
      republic: "Rep.",
      oblast: "Obl.",
      krai: "Krai",
      okrug: "Okr.",
      city: "Fed.",
      other: "Other",
    },
  } as const;

  return labels[language][type];
}

function averageAnnualDelta(
  series: SeriesPoint[],
  selector: (point: SeriesPoint) => number,
  recentYears?: number,
) {
  if (series.length < 2) {
    return 0;
  }

  const startPoint =
    recentYears == null
      ? series[0]
      : series[Math.max(0, series.length - (recentYears + 1))];
  const endPoint = series.at(-1)!;
  const span = endPoint.year - startPoint.year;

  if (span <= 0) {
    return 0;
  }

  return (selector(endPoint) - selector(startPoint)) / span;
}

function buildForecast(series: SeriesPoint[], yearsAhead: number): ForecastPoint | null {
  if (series.length < 2) {
    return null;
  }

  const overallDelta = averageAnnualDelta(series, (point) => point.totalPopulation);
  const recentDelta = averageAnnualDelta(series, (point) => point.totalPopulation, 3);
  const annualDelta = series.length >= 4 ? (overallDelta + recentDelta) / 2 : overallDelta;
  const endPoint = series.at(-1)!;
  const population = Math.max(0, Math.round(endPoint.totalPopulation + annualDelta * yearsAhead));

  return {
    year: endPoint.year + yearsAhead,
    population,
    percentChange:
      endPoint.totalPopulation > 0
        ? ((population - endPoint.totalPopulation) / endPoint.totalPopulation) * 100
        : 0,
  };
}

function shortenName(name: string) {
  return name
    .replace(/^город федерального значения\s+/i, "")
    .replace(/^Республика\s+/i, "")
    .replace(/\s+Республика$/i, "")
    .replace(/\s+область$/i, " обл.")
    .replace(/\s+край$/i, " край")
    .replace(/\s+автономный округ(\s*-\s*Югра)?$/i, (_, suffix = "") => ` АО${suffix}`)
    .replace(/\s+автономная область$/i, " АО")
    .replace(/\s+город федерального значения$/i, "")
    .replace(/\s+/g, " ")
    .trim();
}

export default function Analytics() {
  const { language } = useLanguage();
  const copy = analyticsCopy[language];
  const searchContainerRef = useRef<HTMLDivElement | null>(null);

  const [years, setYears] = useState<number[]>([]);
  const [startYear, setStartYear] = useState(2020);
  const [endYear, setEndYear] = useState(2024);
  const [territoryType, setTerritoryType] = useState<TerritoryType>("all");
  const [selectedTerritoryCode, setSelectedTerritoryCode] = useState<string>(RUSSIA_ID);
  const [regionsStart, setRegionsStart] = useState<MunicipalityData[]>([]);
  const [regionsEnd, setRegionsEnd] = useState<MunicipalityData[]>([]);
  const [series, setSeries] = useState<SeriesPoint[]>([]);
  const [nationalSeries, setNationalSeries] = useState<SeriesPoint[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const deferredQuery = useDeferredValue(searchQuery.trim().toLowerCase());

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      try {
        const payload = await fetchYears();
        if (!active) {
          return;
        }

        const availableYears = payload.years;
        const latestYear = availableYears.at(-1) ?? 2024;
        const initialStart =
          availableYears.find((year) => year >= latestYear - 4) ?? availableYears[0] ?? 2020;

        setYears(availableYears);
        setStartYear(initialStart);
        setEndYear(latestYear);
      } catch (bootstrapError) {
        if (!active) {
          return;
        }

        setError(
          bootstrapError instanceof Error
            ? bootstrapError.message
            : language === "en"
              ? "Failed to load available years"
              : "Не удалось загрузить доступные годы",
        );
        setLoading(false);
      }
    }

    bootstrap();

    return () => {
      active = false;
    };
  }, [language]);

  useEffect(() => {
    if (!years.length) {
      return;
    }

    let active = true;

    async function loadAnalytics() {
      setLoading(true);
      setError(null);

      try {
        const [startRegions, endRegions, trendPayload] = await Promise.all([
          fetchRegions(startYear),
          fetchRegions(endYear),
          fetchTrends(startYear, endYear),
        ]);

        if (!active) {
          return;
        }

        const nextNationalSeries = buildSeriesFromTrend(trendPayload);
        let nextTerritoryCode = selectedTerritoryCode;

        if (
          nextTerritoryCode !== RUSSIA_ID &&
          !endRegions.regions.some((item) => item.code === nextTerritoryCode)
        ) {
          nextTerritoryCode = RUSSIA_ID;
        }

        let nextSeries = nextNationalSeries;
        if (nextTerritoryCode !== RUSSIA_ID) {
          const territorySeries = await fetchTerritorySeries(
            nextTerritoryCode,
            buildYearRange(startYear, endYear),
          );
          const normalizedSeries = territorySeries.map(toSeriesPoint);
          if (normalizedSeries.length >= 2) {
            nextSeries = normalizedSeries;
          }
        }

        if (!active) {
          return;
        }

        setSelectedTerritoryCode(nextTerritoryCode);
        setRegionsStart(startRegions.regions);
        setRegionsEnd(endRegions.regions);
        setNationalSeries(nextNationalSeries);
        setSeries(nextSeries);
      } catch (loadError) {
        if (!active) {
          return;
        }

        setError(
          loadError instanceof Error
            ? loadError.message
            : language === "en"
              ? "Failed to load analytical data"
              : "Не удалось загрузить аналитические данные",
        );
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadAnalytics();

    return () => {
      active = false;
    };
  }, [years, startYear, endYear, selectedTerritoryCode, language]);

  const selectedTerritory =
    selectedTerritoryCode === RUSSIA_ID
      ? null
      : regionsEnd.find((item) => item.code === selectedTerritoryCode) ?? null;
  const selectedSearchLabel = selectedTerritory ? selectedTerritory.name : copy.searchRussia;
  const normalizedSelectedSearchLabel = selectedSearchLabel.trim().toLowerCase();

  useEffect(() => {
    setSearchQuery(selectedSearchLabel);
    setIsSearchOpen(false);
  }, [selectedSearchLabel]);

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!searchContainerRef.current?.contains(event.target as Node)) {
        setIsSearchOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, []);

  const comparisonRows: ComparisonRow[] = regionsEnd
    .map((endRow) => {
      const startRow = regionsStart.find((item) => item.code === endRow.code);

      if (!startRow) {
        return null;
      }

      const absoluteChange = endRow.total_population - startRow.total_population;
      const percentChange =
        startRow.total_population > 0
          ? (absoluteChange / startRow.total_population) * 100
          : 0;

      return {
        code: endRow.code,
        name: endRow.name,
        type: detectTerritoryType(endRow.name),
        startPopulation: startRow.total_population,
        endPopulation: endRow.total_population,
        urbanRatio: endRow.urban_ratio,
        absoluteChange,
        percentChange,
      };
    })
    .filter(Boolean) as ComparisonRow[];

  const filteredRows =
    territoryType === "all"
      ? comparisonRows
      : comparisonRows.filter((item) => item.type === territoryType);

  const searchResults =
    !isSearchOpen || deferredQuery.length < 2 || deferredQuery === normalizedSelectedSearchLabel
      ? []
      : regionsEnd
          .filter(
            (item) =>
              item.code !== selectedTerritoryCode &&
              item.name.toLowerCase().includes(deferredQuery),
          )
          .slice(0, 8);

  const growthRows = [...filteredRows]
    .sort((left, right) => right.percentChange - left.percentChange)
    .slice(0, 6);
  const declineRows = [...filteredRows]
    .sort((left, right) => left.percentChange - right.percentChange)
    .slice(0, 6);
  const registerRows = [...filteredRows]
    .sort((left, right) => Math.abs(right.percentChange) - Math.abs(left.percentChange))
    .slice(0, 14);
  const heatRows = [...filteredRows]
    .sort((left, right) => right.endPopulation - left.endPopulation)
    .slice(0, 24);

  const currentLabel = selectedTerritory?.name ?? copy.allRussia;
  const currentSeries = selectedTerritory ? series : nationalSeries.length ? nationalSeries : series;
  const startPoint = currentSeries[0];
  const endPoint = currentSeries.at(-1);
  const absoluteChange = startPoint && endPoint ? endPoint.totalPopulation - startPoint.totalPopulation : 0;
  const percentChange =
    startPoint && endPoint && startPoint.totalPopulation > 0
      ? (absoluteChange / startPoint.totalPopulation) * 100
      : 0;
  const annualChange = averageAnnualDelta(currentSeries, (point) => point.totalPopulation);
  const forecastFive = buildForecast(currentSeries, 5);
  const chartData = currentSeries.map((point, index) => {
    const previous = currentSeries[index - 1];
    const yearOverYearPercent =
      previous && previous.totalPopulation > 0
        ? ((point.totalPopulation - previous.totalPopulation) / previous.totalPopulation) * 100
        : 0;

    return {
      year: String(point.year),
      total: point.totalPopulation,
      urban: point.urbanPopulation,
      rural: point.ruralPopulation,
      yearOverYearPercent,
    };
  });

  const maxHeatPopulation = Math.max(...heatRows.map((item) => item.endPopulation), 1);
  const maxDynamicsPercent = Math.max(
    ...growthRows.map((item) => Math.abs(item.percentChange)),
    ...declineRows.map((item) => Math.abs(item.percentChange)),
    1,
  );
  const dynamicsSections = [
    {
      key: "growth",
      title: copy.growth,
      rows: growthRows,
      tone: "text-teal-700",
      badge: "bg-teal-600",
      rankSurface: "border-teal-200 bg-teal-50 text-teal-800",
      bar: "linear-gradient(90deg, rgba(13, 148, 136, 0.34), rgba(15, 118, 110, 0.96))",
    },
    {
      key: "decline",
      title: copy.decline,
      rows: declineRows,
      tone: "text-amber-700",
      badge: "bg-amber-600",
      rankSurface: "border-amber-200 bg-amber-50 text-amber-800",
      bar: "linear-gradient(90deg, rgba(217, 119, 6, 0.3), rgba(180, 83, 9, 0.94))",
    },
  ] as const;
  const startYearOptions = years.filter((year) => year <= endYear);
  const endYearOptions = years.filter((year) => year >= startYear);
  const comparisonScopeLabel =
    territoryType === "all" ? copy.allSubjects : getTypeLabel(territoryType, language);
  const contextText = selectedTerritory
    ? language === "en"
      ? `Charts, heat map, and report export are synchronized with ${selectedTerritory.name}.`
      : `Графики, тепловая карта и отчет синхронизированы с ${selectedTerritory.name}.`
    : territoryType !== "all"
      ? language === "en"
        ? `The core series stays at the Russia level, while comparison blocks and export keep the ${comparisonScopeLabel} group in focus.`
        : `Основной ряд остается по России, а сравнительные блоки и выгрузка идут в контексте группы субъектов «${comparisonScopeLabel}».`
      : language === "en"
        ? "Russia-wide data is shown by default. Pick a region or a region group to link the comparison layer and export."
        : "По умолчанию показаны данные по России. Выберите субъект или группу субъектов, чтобы связать сравнительный слой и выгрузку.";
  const reportParams = new URLSearchParams({
    source: "analytics",
    startYear: String(startYear),
    endYear: String(endYear),
    scope: selectedTerritory ? "region" : "russia",
    group: territoryType,
  });
  const reportFocus =
    selectedTerritory != null
      ? language === "en"
        ? `Prepare the report for ${selectedTerritory.name} for ${startYear}-${endYear}.${territoryType !== "all" ? ` Keep the comparison context for the ${comparisonScopeLabel} group.` : ""}`
        : `Подготовь аналитическую справку по ${selectedTerritory.name} за ${startYear}-${endYear} гг.${territoryType !== "all" ? ` Сохрани сравнительный контекст по группе субъектов «${comparisonScopeLabel}».` : ""}`
      : territoryType !== "all"
        ? language === "en"
          ? `Prepare the report for Russia with emphasis on the ${comparisonScopeLabel} group.`
          : `Подготовь аналитическую справку по России с акцентом на группе субъектов «${comparisonScopeLabel}».`
        : "";

  if (selectedTerritory) {
    reportParams.set("regionCode", selectedTerritory.code);
    reportParams.set("regionName", selectedTerritory.name);
  }
  if (reportFocus) {
    reportParams.set("focus", reportFocus);
  }

  const reportHref = `/report?${reportParams.toString()}`;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <main className="mx-auto max-w-[1500px] px-4 py-6 sm:px-8 lg:px-12">
        <header className="border-b border-foreground/10 pb-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-4xl">
              <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-foreground/45">
                {copy.sectionLabel}
              </div>
              <h1
                className="mt-3 text-4xl tracking-[-0.06em] sm:text-5xl"
                style={{ fontFamily: "var(--font-headline)", fontWeight: 800 }}
              >
                {copy.heading}
              </h1>
              <p className="mt-4 max-w-3xl text-base leading-7 text-foreground/65">
                {copy.description}
              </p>
            </div>

            <div className="flex items-center gap-3">
              <LanguageToggle />
              <Link
                to="/"
                className="border border-foreground/10 px-4 py-2 text-sm font-medium text-foreground/72 transition hover:bg-secondary"
              >
                {copy.overview}
              </Link>
              <Link
                to={reportHref}
                className="bg-foreground px-4 py-2 text-sm font-semibold text-background transition hover:opacity-92"
              >
                {copy.report}
              </Link>
            </div>
          </div>
        </header>

        <section className="sticky top-0 z-20 mt-6 border border-foreground/10 bg-background/96 p-4 shadow-[0_18px_48px_rgba(15,23,42,0.08)] backdrop-blur">
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_220px_160px_160px]">
            <div>
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
                {copy.territory}
              </div>
              <div ref={searchContainerRef} className="relative">
                <div className="flex min-h-[56px] border border-foreground/10 bg-white">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedTerritoryCode(RUSSIA_ID);
                      setSearchQuery(copy.searchRussia);
                      setIsSearchOpen(false);
                    }}
                    className={`shrink-0 border-r border-foreground/10 px-4 text-sm font-semibold transition ${
                      selectedTerritoryCode === RUSSIA_ID
                        ? "bg-foreground text-background"
                        : "text-foreground/72 hover:bg-secondary"
                    }`}
                  >
                    {copy.searchRussia}
                  </button>
                  <input
                    value={searchQuery}
                    onFocus={() => setIsSearchOpen(true)}
                    onChange={(event) => {
                      setSearchQuery(event.target.value);
                      setIsSearchOpen(true);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Escape") {
                        setIsSearchOpen(false);
                      }
                    }}
                    placeholder={copy.territoryPlaceholder}
                    className="w-full bg-transparent px-4 py-3 text-sm outline-none placeholder:text-foreground/35"
                  />
                </div>

                {searchResults.length > 0 ? (
                  <div className="absolute inset-x-0 top-[calc(100%+0.45rem)] z-30 max-h-80 overflow-y-auto border border-foreground/10 bg-white shadow-[0_18px_42px_rgba(15,23,42,0.12)]">
                    {searchResults.map((item) => (
                      <button
                        key={`${item.code}-${item.year}`}
                        type="button"
                        onClick={() => {
                          setSelectedTerritoryCode(item.code);
                          setSearchQuery(item.name);
                          setIsSearchOpen(false);
                        }}
                        className="flex w-full items-center justify-between border-b border-foreground/8 px-4 py-3 text-left transition last:border-b-0 hover:bg-secondary"
                      >
                        <span>
                          <span className="block text-sm font-semibold">{item.name}</span>
                          <span className="mt-1 block text-xs text-foreground/45">
                            {getTypeLabel(detectTerritoryType(item.name), language)}
                          </span>
                        </span>
                        <span className="text-sm text-foreground/55">
                          {formatCompactPopulation(item.total_population, language)}
                        </span>
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
              <div className="mt-2 text-xs text-foreground/45">{copy.territoryHint}</div>
            </div>

            <label>
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
                {copy.type}
              </div>
              <select
                value={territoryType}
                onChange={(event) => setTerritoryType(event.target.value as TerritoryType)}
                className="min-h-[56px] w-full border border-foreground/10 bg-white px-4 py-3 text-sm outline-none"
              >
                {(
                  [
                    "all",
                    "republic",
                    "oblast",
                    "krai",
                    "okrug",
                    "city",
                    "other",
                  ] as TerritoryType[]
                ).map((item) => (
                  <option key={item} value={item}>
                    {getTypeLabel(item, language)}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
                {copy.start}
              </div>
              <select
                value={startYear}
                onChange={(event) => {
                  const nextStart = Number(event.target.value);
                  setStartYear(nextStart);
                  if (nextStart > endYear) {
                    setEndYear(nextStart);
                  }
                }}
                className="min-h-[56px] w-full border border-foreground/10 bg-white px-4 py-3 text-sm outline-none"
              >
                {startYearOptions.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
                {copy.end}
              </div>
              <select
                value={endYear}
                onChange={(event) => {
                  const nextEnd = Number(event.target.value);
                  setEndYear(nextEnd);
                  if (nextEnd < startYear) {
                    setStartYear(nextEnd);
                  }
                }}
                className="min-h-[56px] w-full border border-foreground/10 bg-white px-4 py-3 text-sm outline-none"
              >
                {endYearOptions.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </section>

        {error ? (
          <div className="mt-6 border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        <section className="mt-6 grid gap-px border border-foreground/10 bg-foreground/10 xl:grid-cols-[minmax(0,1.55fr)_repeat(3,minmax(0,0.9fr))]">
          <div className="bg-background px-5 py-5">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
              {loading ? copy.loading : copy.focusContext}
            </div>
            <div
              className="mt-2 text-3xl tracking-[-0.05em] sm:text-[2.35rem]"
              style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
            >
              {currentLabel}
            </div>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-foreground/58">{contextText}</p>
          </div>

          <div className="bg-background px-5 py-5">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
              {copy.selectedPeriod}
            </div>
            <div className="mt-3 text-2xl font-semibold tracking-[-0.04em]">
              {startYear}-{endYear}
            </div>
            <div className="mt-2 text-sm text-foreground/55">{copy.mainChartTitle}</div>
          </div>

          <div className="bg-background px-5 py-5">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
              {copy.selectedType}
            </div>
            <div className="mt-3 text-2xl font-semibold tracking-[-0.04em]">
              {comparisonScopeLabel}
            </div>
            <div className="mt-2 text-sm text-foreground/55">
              {formatInteger(filteredRows.length, language)} {copy.metrics.coverage.toLowerCase()}
            </div>
          </div>

          <div className="flex flex-col justify-between gap-4 bg-background px-5 py-5">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
                {copy.reportSync}
              </div>
              <div className="mt-3 text-xl font-semibold tracking-[-0.04em]">
                {copy.reportSyncTitle}
              </div>
              <p className="mt-2 text-sm leading-6 text-foreground/58">{copy.reportSyncText}</p>
            </div>
            <Link
              to={reportHref}
              className="inline-flex min-h-[48px] items-center justify-center border border-foreground/10 px-4 text-sm font-semibold transition hover:bg-secondary"
            >
              {copy.reportSyncAction}
            </Link>
          </div>
        </section>

        <section className="mt-4 grid gap-px border border-foreground/10 bg-foreground/10 md:grid-cols-2 xl:grid-cols-5">
          {[
            {
              label: copy.metrics.population,
              value: endPoint ? formatCompactPopulation(endPoint.totalPopulation, language) : "—",
            },
            {
              label: copy.metrics.change,
              value: endPoint ? formatPercent(percentChange, 1, language) : "—",
            },
            {
              label: copy.metrics.annual,
              value: endPoint ? `${formatSignedInteger(annualChange, language)} ${copy.populationUnit}` : "—",
            },
            {
              label: copy.metrics.urban,
              value: endPoint ? formatCompactPopulation(endPoint.urbanPopulation, language) : "—",
            },
            {
              label: copy.metrics.coverage,
              value: formatInteger(filteredRows.length, language),
            },
          ].map((metric) => (
            <div
              key={metric.label}
              className="flex min-h-[132px] flex-col justify-between bg-background px-4 py-4"
            >
              <div className="text-sm text-foreground/48">{metric.label}</div>
              <div className="text-2xl font-semibold tracking-[-0.04em]">{metric.value}</div>
            </div>
          ))}
        </section>

        <section className="mt-6 grid gap-px border border-foreground/10 bg-foreground/10 xl:grid-cols-[minmax(0,1.35fr)_360px]">
          <div className="flex h-full flex-col bg-white p-4 sm:p-5">
            <div className="flex flex-col gap-2 border-b border-foreground/10 pb-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
                  {copy.mainChartLabel}
                </div>
                <h2
                  className="mt-2 text-2xl tracking-[-0.05em]"
                  style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
                >
                  {copy.mainChartTitle}
                </h2>
              </div>
              <div className="max-w-sm text-sm leading-6 text-foreground/55">{copy.mainChartText}</div>
            </div>

            <div className="mt-4 min-h-[380px] flex-1">
              {chartData.length >= 2 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={chartData}
                    margin={{ top: 12, right: 0, left: -12, bottom: 0 }}
                  >
                    <CartesianGrid stroke="rgba(15, 23, 42, 0.08)" vertical={false} />
                    <XAxis
                      dataKey="year"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fontSize: 12 }}
                      stroke="rgba(15, 23, 42, 0.48)"
                    />
                    <YAxis
                      yAxisId="population"
                      width={82}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(value) =>
                        formatCompactPopulation(Number(value), language)
                      }
                      tick={{ fontSize: 12 }}
                      stroke="rgba(15, 23, 42, 0.48)"
                    />
                    <Tooltip
                      contentStyle={{
                        border: "1px solid rgba(15,23,42,0.1)",
                        borderRadius: "0",
                        background: "#ffffff",
                      }}
                      formatter={(value: number, key) => {
                        const label =
                          key === "urban"
                            ? copy.urbanPopulation
                            : key === "rural"
                              ? copy.ruralPopulation
                              : copy.totalPopulation;

                        return [formatInteger(value, language), label];
                      }}
                    />
                    <Bar
                      yAxisId="population"
                      dataKey="urban"
                      stackId="population"
                      fill="#0f766e"
                      maxBarSize={48}
                    />
                    <Bar
                      yAxisId="population"
                      dataKey="rural"
                      stackId="population"
                      fill="#9c6b3b"
                      maxBarSize={48}
                    />
                    <Line
                      yAxisId="population"
                      type="monotone"
                      dataKey="total"
                      stroke="#111827"
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: "#111827" }}
                      activeDot={{ r: 5, fill: "#111827" }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center border border-dashed border-foreground/12 text-sm text-foreground/45">
                  {copy.noRows}
                </div>
              )}
            </div>

            <div className="mt-4 grid gap-px border border-foreground/10 bg-foreground/10 sm:grid-cols-3">
              {[
                { label: copy.totalPopulation, value: endPoint?.totalPopulation ?? 0, color: "#111827" },
                { label: copy.urbanPopulation, value: endPoint?.urbanPopulation ?? 0, color: "#0f766e" },
                { label: copy.ruralPopulation, value: endPoint?.ruralPopulation ?? 0, color: "#9c6b3b" },
              ].map((item) => (
                <div key={item.label} className="bg-background px-4 py-3">
                  <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-foreground/45">
                    <span className="h-2.5 w-2.5" style={{ backgroundColor: item.color }} />
                    {item.label}
                  </div>
                  <div className="mt-2 text-lg font-semibold tracking-[-0.03em]">
                    {formatCompactPopulation(item.value, language)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-px bg-foreground/10 sm:grid-cols-2 xl:grid-cols-1">
            <div className="bg-white p-4 sm:p-5">
              <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
                {copy.changeChartLabel}
              </div>
              <h2
                className="mt-2 text-2xl tracking-[-0.05em]"
                style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
              >
                {copy.changeChartTitle}
              </h2>
              <p className="mt-3 text-sm leading-6 text-foreground/55">{copy.changeChartText}</p>

              <div className="mt-4 h-[180px]">
                {chartData.length >= 2 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData.slice(1)} margin={{ top: 12, right: 0, left: -8, bottom: 0 }}>
                      <CartesianGrid stroke="rgba(15, 23, 42, 0.08)" vertical={false} />
                      <XAxis
                        dataKey="year"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontSize: 11 }}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(value) => formatPercent(Number(value), 1, language)}
                        tick={{ fontSize: 11 }}
                      />
                      <Tooltip
                        contentStyle={{
                          border: "1px solid rgba(15,23,42,0.1)",
                          borderRadius: "0",
                          background: "#ffffff",
                        }}
                        formatter={(value: number) => [formatPercent(value, 2, language), copy.changeColumn]}
                      />
                      <Bar dataKey="yearOverYearPercent">
                        {chartData.slice(1).map((item) => (
                          <Cell
                            key={item.year}
                            fill={item.yearOverYearPercent >= 0 ? "#0f766e" : "#b45309"}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : null}
              </div>

              {forecastFive ? (
                <div className="mt-4 border border-foreground/10 px-4 py-3 text-sm">
                  <div className="text-foreground/48">
                    {language === "en"
                      ? `Projection for ${forecastFive.year}`
                      : `Оценка на ${forecastFive.year} год`}
                  </div>
                  <div className="mt-2 text-lg font-semibold">
                    {formatCompactPopulation(forecastFive.population, language)}
                  </div>
                  <div className="mt-1 text-foreground/55">
                    {formatPercent(forecastFive.percentChange, 1, language)}
                  </div>
                </div>
              ) : null}
            </div>

            <div className="bg-white p-4 sm:p-5">
              <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
                {copy.indicatorsLabel}
              </div>
              <h2
                className="mt-2 text-2xl tracking-[-0.05em]"
                style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
              >
                {copy.indicatorsTitle}
              </h2>
              <p className="mt-3 text-sm leading-6 text-foreground/55">{copy.indicatorsNote}</p>

              <div className="mt-5 divide-y divide-foreground/10 border-y border-foreground/10">
                {[
                  copy.birthRate,
                  copy.deathRate,
                  copy.naturalIncrease,
                  copy.migration,
                ].map((label) => (
                  <div key={label} className="grid grid-cols-[minmax(0,1fr)_120px] gap-3 py-3 text-sm">
                    <div>{label}</div>
                    <div className="text-right text-foreground/45">{copy.notAvailable}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mt-6 border border-foreground/10 bg-white">
          <div className="flex flex-col gap-2 border-b border-foreground/10 px-4 py-4 sm:flex-row sm:items-end sm:justify-between sm:px-5">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
                {copy.growthLabel}
              </div>
              <h2
                className="mt-2 text-2xl tracking-[-0.05em]"
                style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
              >
                {copy.growthTitle}
              </h2>
            </div>
            <div className="text-sm text-foreground/55">
              {comparisonScopeLabel} · {startYear}-{endYear}
            </div>
          </div>

          <div className="divide-y divide-foreground/8">
            {dynamicsSections.map((section) => (
              <div key={section.key} className="px-4 py-5 sm:px-5">
                <div className="mb-4 inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.18em]">
                  <span className={`h-2.5 w-2.5 rounded-full ${section.badge}`} />
                  <span className={section.tone}>{section.title}</span>
                </div>

                {section.rows.length ? (
                  <div className="space-y-2">
                    {section.rows.map((item, index) => {
                      const selected = selectedTerritoryCode === item.code;
                      const progress = Math.max(
                        (Math.abs(item.percentChange) / maxDynamicsPercent) * 100,
                        12,
                      );

                      return (
                        <button
                          key={`${section.key}-${item.code}`}
                          type="button"
                          onClick={() => setSelectedTerritoryCode(item.code)}
                          className={`w-full border px-4 py-4 text-left transition ${
                            selected
                              ? "border-foreground/18 bg-secondary/55"
                              : "border-foreground/10 bg-background hover:bg-secondary/35"
                          }`}
                        >
                          <div className="flex items-start gap-4">
                            <div
                              className={`flex h-11 w-11 shrink-0 items-center justify-center border text-lg font-semibold tracking-[-0.05em] ${section.rankSurface}`}
                            >
                              {index + 1}
                            </div>

                            <div className="min-w-0 flex-1">
                              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                                <div className="min-w-0">
                                  <div className="text-lg font-semibold tracking-[-0.03em]">
                                    {item.name}
                                  </div>
                                  <div className="mt-1 text-xs uppercase tracking-[0.18em] text-foreground/42">
                                    {getTypeLabel(item.type, language)}
                                  </div>
                                </div>

                                <div className="grid gap-3 sm:grid-cols-2 lg:min-w-[320px]">
                                  <div>
                                    <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground/42">
                                      {copy.endPopulationColumn}
                                    </div>
                                    <div className="mt-1 text-sm font-medium text-foreground/72">
                                      {formatCompactPopulation(item.endPopulation, language)}
                                    </div>
                                  </div>
                                  <div>
                                    <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground/42">
                                      {copy.changeColumn}
                                    </div>
                                    <div className={`mt-1 text-sm font-semibold ${section.tone}`}>
                                      {formatSignedInteger(item.absoluteChange, language)} /{" "}
                                      {formatPercent(item.percentChange, 1, language)}
                                    </div>
                                  </div>
                                </div>
                              </div>

                              <div className="mt-4 h-2 overflow-hidden bg-secondary">
                                <div
                                  className="h-full"
                                  style={{
                                    width: `${progress}%`,
                                    background: section.bar,
                                  }}
                                />
                              </div>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  <div className="border border-dashed border-foreground/12 px-4 py-5 text-sm text-foreground/45">
                    {copy.noRows}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="mt-6 border border-foreground/10 bg-white p-4 sm:p-5">
          <div className="flex flex-col gap-2 border-b border-foreground/10 pb-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
                {copy.heatmapLabel}
              </div>
              <h2
                className="mt-2 text-2xl tracking-[-0.05em]"
                style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
              >
                {copy.heatmapTitle}
              </h2>
            </div>
            <div className="max-w-xl text-sm leading-6 text-foreground/55">{copy.heatmapText}</div>
          </div>

          <div className="mt-4 flex items-center gap-3 text-xs uppercase tracking-[0.18em] text-foreground/45">
            <span>{copy.heatScaleLow}</span>
            <div className="h-2 flex-1 bg-[linear-gradient(90deg,rgba(0,96,100,0.14),rgba(0,96,100,0.9))]" />
            <span>{copy.heatScaleHigh}</span>
          </div>

          {heatRows.length ? (
            <div className="mt-6 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6">
              {heatRows.map((item) => {
                const intensity = item.endPopulation / maxHeatPopulation;
                const selected = selectedTerritoryCode === item.code;
                const startAlpha = 0.12 + intensity * 0.22;
                const endAlpha = intensity > 0.58 ? 0.48 + intensity * 0.3 : 0.18 + intensity * 0.26;
                const background = `linear-gradient(145deg, rgba(0, 96, 100, ${startAlpha}), rgba(0, 96, 100, ${endAlpha}))`;
                const textColor = intensity > 0.6 ? "#f8fafc" : "#0f172a";
                const borderColor = selected ? "#0a0a0a" : "rgba(15, 23, 42, 0.08)";

                return (
                  <button
                    key={item.code}
                    type="button"
                    onClick={() => setSelectedTerritoryCode(item.code)}
                    title={item.name}
                    className="flex min-h-[116px] flex-col justify-between overflow-hidden border p-3 text-left transition hover:-translate-y-0.5"
                    style={{
                      background,
                      color: textColor,
                      borderColor,
                      boxShadow: selected ? "inset 0 0 0 1px rgba(10, 10, 10, 0.55)" : "none",
                    }}
                  >
                    <div className="shrink-0 text-[10px] uppercase tracking-[0.18em] opacity-70">
                      {getHeatmapTypeLabel(item.type, language)}
                    </div>
                    <div className="mt-3 flex-1 overflow-hidden text-[13px] font-semibold leading-[1.08rem] break-words [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:4]">
                      {shortenName(item.name)}
                    </div>
                    <div className="mt-3 shrink-0 text-xs opacity-80">
                      {formatCompactPopulation(item.endPopulation, language)}
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="mt-6 border border-dashed border-foreground/12 px-4 py-5 text-sm text-foreground/45">
              {copy.noRows}
            </div>
          )}
        </section>

        <section className="mt-6 border border-foreground/10 bg-white p-4 sm:p-5">
          <div className="flex flex-col gap-2 border-b border-foreground/10 pb-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground/45">
                {copy.registerLabel}
              </div>
              <h2
                className="mt-2 text-2xl tracking-[-0.05em]"
                style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
              >
                {copy.registerTitle}
              </h2>
            </div>
            <div className="max-w-xl text-sm leading-6 text-foreground/55">{copy.registerText}</div>
          </div>

          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-foreground/10 text-left text-foreground/45">
                  <th className="pb-3 pr-4 font-medium">{copy.territoryColumn}</th>
                  <th className="pb-3 pr-4 font-medium">{copy.typeColumn}</th>
                  <th className="pb-3 pr-4 font-medium">{copy.endPopulationColumn}</th>
                  <th className="pb-3 pr-4 font-medium">{copy.changeColumn}</th>
                  <th className="pb-3 text-right font-medium">{copy.urbanShareColumn}</th>
                </tr>
              </thead>
              <tbody>
                {registerRows.map((item) => (
                  <tr key={item.code} className="border-b border-foreground/8 transition hover:bg-secondary">
                    <td className="py-3 pr-4">
                      <button
                        type="button"
                        onClick={() => setSelectedTerritoryCode(item.code)}
                        className="text-left font-medium"
                      >
                        {item.name}
                      </button>
                    </td>
                    <td className="py-3 pr-4 text-foreground/55">
                      {getTypeLabel(item.type, language)}
                    </td>
                    <td className="py-3 pr-4">
                      {formatCompactPopulation(item.endPopulation, language)}
                    </td>
                    <td className="py-3 pr-4">
                      <span className={item.absoluteChange >= 0 ? "text-teal-700" : "text-amber-700"}>
                        {formatSignedInteger(item.absoluteChange, language)} /{" "}
                        {formatPercent(item.percentChange, 1, language)}
                      </span>
                    </td>
                    <td className="py-3 text-right">
                      {formatPercent(item.urbanRatio * 100, 1, language)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
