import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router";

import LanguageToggle from "./LanguageToggle";
import {
  fetchRegions,
  fetchTerritorySeries,
  fetchTrends,
  fetchYears,
  generateReport,
  resolveDownloadUrl,
  type MunicipalityData,
  type ReportGenerationResponse,
  type Scope,
} from "../lib/api";
import {
  formatCompactPopulation,
  formatDateTime,
  formatFileSize,
  formatPercent,
  formatPoints,
  formatSignedInteger,
} from "../lib/format";
import { useLanguage, type AppLanguage } from "../lib/language";
import {
  buildInsights,
  buildSeriesFromTrend,
  buildYearRange,
  toSeriesPoint,
  type SeriesPoint,
} from "../lib/insights";

function pickDefaultRegion(regions: MunicipalityData[]) {
  return (
    regions.find((item) => item.name.toLowerCase() === "московская область") ??
    regions[0] ??
    null
  );
}

type AnalyticsGroup = "all" | "republic" | "oblast" | "krai" | "okrug" | "city" | "other";

function isAnalyticsGroup(value: string | null): value is AnalyticsGroup {
  return (
    value === "all" ||
    value === "republic" ||
    value === "oblast" ||
    value === "krai" ||
    value === "okrug" ||
    value === "city" ||
    value === "other"
  );
}

function getAnalyticsGroupLabel(group: AnalyticsGroup, language: AppLanguage) {
  const labels = {
    ru: {
      all: "Все субъекты",
      republic: "Республики",
      oblast: "Области",
      krai: "Края",
      okrug: "Округа",
      city: "Города федерального значения",
      other: "Прочие",
    },
    en: {
      all: "All regions",
      republic: "Republics",
      oblast: "Oblasts",
      krai: "Krais",
      okrug: "Okrugs",
      city: "Federal cities",
      other: "Other",
    },
  } as const;

  return labels[language][group];
}

const reportCopy = {
  ru: {
    workspace: "Подготовка отчета",
    title: "Формирование аналитического отчета",
    analytics: "К аналитике",
    parameters: "Параметры выгрузки",
    territoryReport: "Отчет по территории",
    scope: "Основа отчета",
    region: "Субъект РФ",
    russiaScope: "Россия",
    regionScope: "Субъект РФ",
    periodStart: "Начало периода",
    periodEnd: "Конец периода",
    linkedAnalytics: "Контекст из аналитики",
    linkedAnalyticsText:
      "Период, выбранный субъект и сравнительный срез перенесены из экрана аналитики. При необходимости можно уточнить акцент перед генерацией.",
    linkedSlice: "Срез сравнения",
    download: "Скачать",
    extraSummary: "Добавить итоговое заключение",
    extraSummaryText:
      "Система попробует дополнить отчет кратким итоговым блоком на основе выбранного периода и территории.",
    focus: "Пользовательский акцент",
    focusPlaceholder:
      "Например: сделай акцент на урбанизации и последствиях для территориального планирования.",
    generate: "Сформировать и подготовить файлы",
    generating: "Формирую DOCX и PDF...",
    files: "Готовые файлы",
    generatedAt: "Сформировано",
    preview: "Предварительный просмотр",
    report: "Аналитический отчет",
    latest: "Последняя генерация",
    period: "Период",
    loadingPreview: "Подготавливаю превью отчета...",
    metrics: {
      endPopulation: "Население на конец периода",
      change: "Изменение за период",
      urbanization: "Урбанизация",
      urbanShareChange: "Изменение доли города",
    },
    sections: {
      summary: "Краткое резюме динамики населения",
      trends: "Выявленные демографические тенденции и возможные факторы влияния",
      forecast: "Прогнозная оценка на 5-10 лет",
      recommendations: "Рекомендации по социальной политике и территориальному планированию",
    },
    forecastTable: {
      horizon: "Горизонт",
      year: "Год",
      population: "Население",
      change: "Изменение",
      afterFive: "Через 5 лет",
      afterTen: "Через 10 лет",
    },
    exportNote:
      "Экспортируемая версия будет сформирована из текущего набора данных и дополнительно включит таблицы и файлы выгрузки.",
  },
  en: {
    workspace: "Report preparation",
    title: "Analytical report generation",
    analytics: "Back to analytics",
    parameters: "Export parameters",
    territoryReport: "Territory report",
    scope: "Report base",
    region: "Region",
    russiaScope: "Russia",
    regionScope: "Region",
    periodStart: "Start year",
    periodEnd: "End year",
    linkedAnalytics: "Linked analytics context",
    linkedAnalyticsText:
      "The selected period, region, and comparison slice were transferred from analytics. You can refine the focus before generation.",
    linkedSlice: "Comparison slice",
    download: "Download",
    extraSummary: "Add summary block",
    extraSummaryText:
      "The system will try to append a short conclusion based on the selected period and territory.",
    focus: "User focus",
    focusPlaceholder:
      "For example: focus on urbanization and implications for territorial planning.",
    generate: "Generate and prepare files",
    generating: "Generating DOCX and PDF...",
    files: "Generated files",
    generatedAt: "Generated",
    preview: "Preview",
    report: "Analytical report",
    latest: "Latest generation",
    period: "Period",
    loadingPreview: "Preparing report preview...",
    metrics: {
      endPopulation: "Population at end of period",
      change: "Change over period",
      urbanization: "Urbanization",
      urbanShareChange: "Urban share change",
    },
    sections: {
      summary: "Population dynamics summary",
      trends: "Observed demographic trends and possible drivers",
      forecast: "Forecast horizon for the next 5-10 years",
      recommendations: "Recommendations for social policy and territorial planning",
    },
    forecastTable: {
      horizon: "Horizon",
      year: "Year",
      population: "Population",
      change: "Change",
      afterFive: "In 5 years",
      afterTen: "In 10 years",
    },
    exportNote:
      "The exported version is assembled from the current dataset and includes the generated tables and download files.",
  },
} as const;

export default function Report() {
  const { language } = useLanguage();
  const copy = reportCopy[language];
  const [searchParams] = useSearchParams();
  const initialParamsAppliedRef = useRef(false);
  const linkedGroupParam = searchParams.get("group");
  const [scope, setScope] = useState<Scope>("russia");
  const [years, setYears] = useState<number[]>([]);
  const [regions, setRegions] = useState<MunicipalityData[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<MunicipalityData | null>(null);
  const [startYear, setStartYear] = useState(2020);
  const [endYear, setEndYear] = useState(2024);
  const [includeAiSummary, setIncludeAiSummary] = useState(true);
  const [focusPrompt, setFocusPrompt] = useState("");
  const [previewLoading, setPreviewLoading] = useState(true);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [generatedReport, setGeneratedReport] = useState<ReportGenerationResponse | null>(null);
  const [generating, setGenerating] = useState(false);
  const [series, setSeries] = useState<SeriesPoint[]>([]);
  const [nationalSeries, setNationalSeries] = useState<SeriesPoint[]>([]);
  const linkedFromAnalytics = searchParams.get("source") === "analytics";
  const linkedGroup = isAnalyticsGroup(linkedGroupParam) ? linkedGroupParam : null;
  const linkedGroupLabel = linkedGroup ? getAnalyticsGroupLabel(linkedGroup, language) : null;
  const linkedRegionName = searchParams.get("regionName");

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      try {
        const yearsPayload = await fetchYears();
        if (!active) {
          return;
        }

        const availableYears = yearsPayload.years;
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

        setPreviewError(
          bootstrapError instanceof Error
            ? bootstrapError.message
            : "Не удалось загрузить доступные годы",
        );
        setPreviewLoading(false);
      }
    }

    bootstrap();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!endYear) {
      return;
    }

    let active = true;

    async function loadRegions() {
      try {
        const regionsPayload = await fetchRegions(endYear);
        if (!active) {
          return;
        }

        setRegions(regionsPayload.regions);
        setSelectedRegion((current) => {
          if (!current) {
            return pickDefaultRegion(regionsPayload.regions);
          }
          return regionsPayload.regions.find((item) => item.code === current.code) ?? current;
        });
      } catch (regionsError) {
        if (!active) {
          return;
        }

        setPreviewError(
          regionsError instanceof Error ? regionsError.message : "Не удалось получить регионы",
        );
      }
    }

    loadRegions();

    return () => {
      active = false;
    };
  }, [endYear]);

  useEffect(() => {
    if (initialParamsAppliedRef.current || !years.length) {
      return;
    }

    const requestedScope = searchParams.get("scope");
    const requestedRegionCode = searchParams.get("regionCode");
    const requestedRegionName = searchParams.get("regionName");
    const requestedFocus = searchParams.get("focus");
    const requestedStart = Number(searchParams.get("startYear"));
    const requestedEnd = Number(searchParams.get("endYear"));

    if (requestedScope === "region" && !regions.length) {
      return;
    }

    let nextStart = years.includes(requestedStart) ? requestedStart : startYear;
    let nextEnd = years.includes(requestedEnd) ? requestedEnd : endYear;
    if (nextStart > nextEnd) {
      [nextStart, nextEnd] = [nextEnd, nextStart];
    }

    setStartYear(nextStart);
    setEndYear(nextEnd);

    if (requestedScope === "region") {
      setScope("region");
      const nextRegion =
        regions.find((item) => item.code === requestedRegionCode) ??
        regions.find((item) => item.name.toLowerCase() === requestedRegionName?.toLowerCase()) ??
        pickDefaultRegion(regions);
      setSelectedRegion(nextRegion);
    } else if (requestedScope === "russia") {
      setScope("russia");
    }

    if (requestedFocus) {
      setFocusPrompt((current) => current || requestedFocus);
    }

    initialParamsAppliedRef.current = true;
  }, [years, regions, searchParams, startYear, endYear]);

  useEffect(() => {
    if (!years.length) {
      return;
    }

    let active = true;

    async function loadPreview() {
      if (scope === "region" && !selectedRegion) {
        return;
      }

      setPreviewLoading(true);
      setPreviewError(null);

      try {
        const nationalTrend = await fetchTrends(startYear, endYear);
        const normalizedNationalSeries = buildSeriesFromTrend(nationalTrend);
        let nextSeries = normalizedNationalSeries;

        if (scope === "region" && selectedRegion) {
          const regionSeries = await fetchTerritorySeries(
            selectedRegion.code,
            buildYearRange(startYear, endYear),
          );
          nextSeries = regionSeries.map(toSeriesPoint);
        }

        if (!active) {
          return;
        }

        if (nextSeries.length < 2) {
          throw new Error("Недостаточно данных для предварительного просмотра справки");
        }

        setSeries(nextSeries);
        setNationalSeries(normalizedNationalSeries);
      } catch (previewLoadError) {
        if (!active) {
          return;
        }

        setPreviewError(
          previewLoadError instanceof Error
            ? previewLoadError.message
            : "Не удалось подготовить превью справки",
        );
      } finally {
        if (active) {
          setPreviewLoading(false);
        }
      }
    }

    loadPreview();

    return () => {
      active = false;
    };
  }, [years, startYear, endYear, scope, selectedRegion]);

  const label = scope === "russia" ? copy.russiaScope : selectedRegion?.name ?? copy.regionScope;
  const insights = buildInsights(
    label,
    series,
    scope === "region" ? nationalSeries : undefined,
  );

  const yearStartOptions = years.filter((year) => year <= endYear);
  const yearEndOptions = years.filter((year) => year >= startYear);
  const previewMetrics = [
    {
      label: copy.metrics.endPopulation,
      value: insights ? formatCompactPopulation(insights.end.totalPopulation, language) : "—",
    },
    {
      label: copy.metrics.change,
      value: insights
        ? `${formatSignedInteger(insights.absoluteChange, language)} ${language === "en" ? "people" : "чел."}`
        : "—",
    },
    {
      label: copy.metrics.urbanization,
      value: insights ? formatPercent(insights.end.urbanRatio * 100, 1, language) : "—",
    },
    {
      label: copy.metrics.urbanShareChange,
      value: insights ? formatPoints(insights.urbanRatioChangePp, 2, language) : "—",
    },
  ];
  const forecastRows = insights
    ? [
        {
          label: copy.forecastTable.afterFive,
          year: insights.forecastFive.forecastYear,
          population: formatCompactPopulation(insights.forecastFive.population, language),
          change: formatPercent(insights.forecastFive.percentChange, 1, language),
        },
        {
          label: copy.forecastTable.afterTen,
          year: insights.forecastTen.forecastYear,
          population: formatCompactPopulation(insights.forecastTen.population, language),
          change: formatPercent(insights.forecastTen.percentChange, 1, language),
        },
      ]
    : [];

  async function handleGenerateReport() {
    setGenerating(true);
    setGeneratedReport(null);

    try {
      const response = await generateReport({
        start_year: startYear,
        end_year: endYear,
        scope,
        region_name: scope === "region" ? selectedRegion?.name : undefined,
        format: "both",
        focus_prompt: focusPrompt.trim() || undefined,
        include_ai_summary: includeAiSummary,
      });
      setGeneratedReport(response);
    } catch (generationError) {
      setPreviewError(
        generationError instanceof Error
          ? generationError.message
          : "Не удалось сформировать справку",
      );
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-foreground/8 bg-background/88 backdrop-blur">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-3 px-4 py-4 sm:px-8 lg:flex-row lg:items-center lg:justify-between lg:px-16">
          <div className="flex items-center gap-5">
            <Link to="/" className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center bg-primary text-primary-foreground">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-foreground/35">
                  {copy.workspace}
                </div>
                <div
                  className="text-xl tracking-[-0.04em]"
                  style={{ fontFamily: "var(--font-headline)", fontWeight: 800 }}
                >
                  Демографика
                </div>
              </div>
            </Link>
            <div className="hidden text-foreground/22 lg:block">/</div>
            <div className="hidden text-sm font-medium text-foreground/55 lg:block">
              {copy.title}
            </div>
          </div>

          <div className="flex items-center gap-4 text-sm">
            <LanguageToggle />
            <Link to="/analytics" className="font-medium text-foreground/65 transition-colors hover:text-foreground">
              {copy.analytics}
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1440px] gap-6 px-4 py-6 sm:px-8 xl:grid-cols-[380px_minmax(0,1fr)] lg:px-16 lg:py-10">
        <aside className="border border-foreground/8 bg-white/90 p-6 shadow-[0_24px_72px_rgba(15,23,42,0.04)] xl:sticky xl:top-6 xl:h-fit">
          <div className="space-y-6">
            <div>
              <div className="text-sm font-semibold uppercase tracking-[0.22em] text-foreground/38">
                {copy.parameters}
              </div>
              <h1
                className="mt-3 text-3xl tracking-[-0.05em]"
                style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
              >
                {copy.territoryReport}
              </h1>
            </div>

            {linkedFromAnalytics ? (
              <div className="border border-primary/12 bg-primary/5 px-4 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.22em] text-primary/70">
                  {copy.linkedAnalytics}
                </div>
                <p className="mt-2 text-sm leading-6 text-foreground/65">
                  {copy.linkedAnalyticsText}
                </p>
                <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                  <div className="border border-foreground/8 bg-white px-3 py-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground/42">
                      {copy.scope}
                    </div>
                    <div className="mt-1 text-sm font-semibold">
                      {linkedRegionName ?? copy.russiaScope}
                    </div>
                  </div>
                  {linkedGroupLabel ? (
                    <div className="border border-foreground/8 bg-white px-3 py-3">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground/42">
                        {copy.linkedSlice}
                      </div>
                      <div className="mt-1 text-sm font-semibold">{linkedGroupLabel}</div>
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}

            <div className="space-y-5">
              <label className="block space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-foreground/42">
                  {copy.scope}
                </span>
                <select
                  value={scope}
                  onChange={(event) => setScope(event.target.value as Scope)}
                  className="w-full border border-foreground/10 bg-secondary px-4 py-3 text-sm font-medium outline-none transition focus:border-primary/30 focus:ring-2 focus:ring-primary/10"
                >
                  <option value="russia">{copy.russiaScope}</option>
                  <option value="region">{copy.regionScope}</option>
                </select>
              </label>

              {scope === "region" ? (
                <label className="block space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.2em] text-foreground/42">
                    {copy.region}
                  </span>
                  <select
                    value={selectedRegion?.code ?? ""}
                    onChange={(event) =>
                      setSelectedRegion(
                        regions.find((item) => item.code === event.target.value) ?? null,
                      )
                    }
                    className="w-full border border-foreground/10 bg-secondary px-4 py-3 text-sm font-medium outline-none transition focus:border-primary/30 focus:ring-2 focus:ring-primary/10"
                  >
                    {regions.map((item) => (
                      <option key={item.code} value={item.code}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.2em] text-foreground/42">
                    {copy.periodStart}
                  </span>
                  <select
                    value={startYear}
                    onChange={(event) => {
                      const nextStart = Number(event.target.value);
                      setStartYear(nextStart);
                      if (nextStart > endYear) {
                        setEndYear(nextStart);
                      }
                    }}
                    className="w-full border border-foreground/10 bg-secondary px-4 py-3 text-sm font-medium outline-none transition focus:border-primary/30 focus:ring-2 focus:ring-primary/10"
                  >
                    {yearStartOptions.map((year) => (
                      <option key={year} value={year}>
                        {year}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.2em] text-foreground/42">
                    {copy.periodEnd}
                  </span>
                  <select
                    value={endYear}
                    onChange={(event) => {
                      const nextEnd = Number(event.target.value);
                      setEndYear(nextEnd);
                      if (nextEnd < startYear) {
                        setStartYear(nextEnd);
                      }
                    }}
                    className="w-full border border-foreground/10 bg-secondary px-4 py-3 text-sm font-medium outline-none transition focus:border-primary/30 focus:ring-2 focus:ring-primary/10"
                  >
                    {yearEndOptions.map((year) => (
                      <option key={year} value={year}>
                        {year}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label className="flex items-start gap-3 border border-foreground/8 bg-secondary px-4 py-4">
                <input
                  type="checkbox"
                  checked={includeAiSummary}
                  onChange={(event) => setIncludeAiSummary(event.target.checked)}
                  className="mt-1 h-4 w-4 border border-foreground/20 text-primary"
                />
                <span>
                  <span className="block text-sm font-semibold">{copy.extraSummary}</span>
                  <span className="mt-1 block text-sm leading-6 text-foreground/58">
                    {copy.extraSummaryText}
                  </span>
                </span>
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-foreground/42">
                  {copy.focus}
                </span>
                <textarea
                  value={focusPrompt}
                  onChange={(event) => setFocusPrompt(event.target.value)}
                  rows={4}
                  placeholder={copy.focusPlaceholder}
                  className="w-full border border-foreground/10 bg-secondary px-4 py-3 text-sm leading-6 outline-none transition placeholder:text-foreground/35 focus:border-primary/30 focus:ring-2 focus:ring-primary/10"
                />
              </label>

              <button
                type="button"
                onClick={handleGenerateReport}
                disabled={generating || previewLoading || (scope === "region" && !selectedRegion)}
                className="inline-flex w-full items-center justify-center bg-primary px-6 py-4 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/15 transition-transform hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {generating ? copy.generating : copy.generate}
              </button>
            </div>

            {generatedReport ? (
              <div className="border-t border-foreground/8 pt-6">
                <div className="text-xs font-semibold uppercase tracking-[0.22em] text-foreground/38">
                  {copy.files}
                </div>
                <div className="mt-4 space-y-3">
                  {generatedReport.files.map((file) => (
                    <a
                      key={file.filename}
                      href={resolveDownloadUrl(file.download_url)}
                      className="flex items-center justify-between gap-4 border border-foreground/8 bg-secondary px-4 py-4 transition-colors hover:bg-secondary/80"
                    >
                      <span className="min-w-0">
                        <span className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground/42">
                          {file.format}
                        </span>
                        <span className="mt-1 block truncate text-sm font-semibold">
                          {file.filename}
                        </span>
                        <span className="mt-1 block text-sm text-foreground/55">
                          {formatFileSize(file.size_bytes, language)}
                        </span>
                      </span>
                      <span className="shrink-0 text-sm font-medium text-primary">
                        {copy.download}
                      </span>
                    </a>
                  ))}
                </div>

                <div className="mt-4 text-sm text-foreground/55">
                  {copy.generatedAt} {formatDateTime(generatedReport.created_at, language)}
                </div>
              </div>
            ) : null}
          </div>
        </aside>

        <section className="overflow-hidden border border-foreground/8 bg-white/94 shadow-[0_25px_80px_rgba(15,23,42,0.05)]">
          <div className="border-b border-foreground/8 bg-[linear-gradient(180deg,rgba(240,238,233,0.92),rgba(255,255,255,0.95))] px-6 py-6 sm:px-10">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <div className="text-sm font-semibold uppercase tracking-[0.24em] text-foreground/40">
                  {copy.preview}
                </div>
                <h2
                  className="mt-3 text-3xl tracking-[-0.05em] sm:text-4xl"
                  style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
                >
                  {copy.report}
                </h2>
                <div className="mt-2 text-lg text-foreground/65">{label}</div>
                {linkedGroupLabel ? (
                  <div className="mt-3 inline-flex border border-foreground/10 bg-white/70 px-3 py-2 text-sm text-foreground/65">
                    {copy.linkedSlice}: {linkedGroupLabel}
                  </div>
                ) : null}
              </div>

              <div className="text-sm text-foreground/50">
                {generatedReport
                  ? `${copy.latest}: ${formatDateTime(generatedReport.created_at, language)}`
                  : `${copy.period}: ${startYear}-${endYear}`}
              </div>
            </div>
          </div>

          <div className="px-6 py-8 sm:px-10">
            {previewError ? (
              <div className="border border-destructive/15 bg-destructive/5 px-5 py-4 text-sm text-destructive">
                {previewError}
              </div>
            ) : null}

            <div className="grid gap-3 border-b border-foreground/8 pb-8 sm:grid-cols-2 xl:grid-cols-4">
              {previewMetrics.map((metric) => (
                <div
                  key={metric.label}
                  className="border border-foreground/8 bg-secondary/35 px-4 py-4"
                >
                  <div className="text-sm text-foreground/45">{metric.label}</div>
                  <div className="mt-2 text-xl font-semibold tracking-[-0.04em]">
                    {metric.value}
                  </div>
                </div>
              ))}
            </div>

            {previewLoading ? (
              <div className="mt-8 border border-foreground/8 bg-secondary/35 px-5 py-5 text-sm text-foreground/60">
                {copy.loadingPreview}
              </div>
            ) : insights ? (
              <article className="mt-8 space-y-4">
                <section className="border border-foreground/8 bg-background/40 px-5 py-5 sm:px-6">
                  <div className="flex flex-col gap-5 sm:flex-row">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center border border-foreground/10 bg-white text-lg font-semibold tracking-[-0.05em]">
                      01
                    </div>
                    <div className="min-w-0">
                      <h3
                        className="text-2xl tracking-[-0.04em]"
                        style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
                      >
                        {copy.sections.summary}
                      </h3>
                      <div className="mt-4 space-y-4 text-base leading-8 text-foreground/78">
                        {insights.summaryParagraphs.map((paragraph) => (
                          <p key={paragraph}>{paragraph}</p>
                        ))}
                      </div>
                    </div>
                  </div>
                </section>

                <section className="border border-foreground/8 bg-background/40 px-5 py-5 sm:px-6">
                  <div className="flex flex-col gap-5 sm:flex-row">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center border border-foreground/10 bg-white text-lg font-semibold tracking-[-0.05em]">
                      02
                    </div>
                    <div className="min-w-0">
                      <h3
                        className="text-2xl tracking-[-0.04em]"
                        style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
                      >
                        {copy.sections.trends}
                      </h3>
                      <div className="mt-4 space-y-4 text-base leading-8 text-foreground/78">
                        {insights.trendParagraphs.map((paragraph) => (
                          <p key={paragraph}>{paragraph}</p>
                        ))}
                      </div>
                    </div>
                  </div>
                </section>

                <section className="border border-foreground/8 bg-background/40 px-5 py-5 sm:px-6">
                  <div className="flex flex-col gap-5 sm:flex-row">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center border border-foreground/10 bg-white text-lg font-semibold tracking-[-0.05em]">
                      03
                    </div>
                    <div className="min-w-0">
                      <h3
                        className="text-2xl tracking-[-0.04em]"
                        style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
                      >
                        {copy.sections.forecast}
                      </h3>
                      <div className="mt-4 space-y-4 text-base leading-8 text-foreground/78">
                        {insights.forecastParagraphs.map((paragraph) => (
                          <p key={paragraph}>{paragraph}</p>
                        ))}
                      </div>

                      <div className="mt-6 overflow-hidden border border-foreground/8 bg-white">
                        <div className="hidden grid-cols-[minmax(0,1.2fr)_90px_160px_120px] gap-4 border-b border-foreground/8 bg-secondary px-4 py-3 text-sm font-semibold text-foreground/60 sm:grid">
                          <div>{copy.forecastTable.horizon}</div>
                          <div>{copy.forecastTable.year}</div>
                          <div>{copy.forecastTable.population}</div>
                          <div>{copy.forecastTable.change}</div>
                        </div>

                        {forecastRows.map((row) => (
                          <div
                            key={row.label}
                            className="grid gap-3 border-t border-foreground/8 px-4 py-4 text-sm first:border-t-0 sm:grid-cols-[minmax(0,1.2fr)_90px_160px_120px] sm:items-center"
                          >
                            <div>
                              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground/42 sm:hidden">
                                {copy.forecastTable.horizon}
                              </div>
                              <div className="font-medium">{row.label}</div>
                            </div>
                            <div>
                              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground/42 sm:hidden">
                                {copy.forecastTable.year}
                              </div>
                              {row.year}
                            </div>
                            <div>
                              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground/42 sm:hidden">
                                {copy.forecastTable.population}
                              </div>
                              {row.population}
                            </div>
                            <div>
                              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground/42 sm:hidden">
                                {copy.forecastTable.change}
                              </div>
                              {row.change}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </section>

                <section className="border border-foreground/8 bg-background/40 px-5 py-5 sm:px-6">
                  <div className="flex flex-col gap-5 sm:flex-row">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center border border-foreground/10 bg-white text-lg font-semibold tracking-[-0.05em]">
                      04
                    </div>
                    <div className="min-w-0">
                      <h3
                        className="text-2xl tracking-[-0.04em]"
                        style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
                      >
                        {copy.sections.recommendations}
                      </h3>
                      <ol className="mt-4 grid gap-3 lg:grid-cols-2">
                        {insights.recommendations.map((item, index) => (
                          <li
                            key={item}
                            className="flex items-start gap-3 border border-foreground/8 bg-white px-4 py-4"
                          >
                            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center border border-foreground/10 bg-secondary text-sm font-semibold">
                              {index + 1}
                            </span>
                            <span className="text-sm leading-6 text-foreground/75">{item}</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  </div>
                </section>
              </article>
            ) : null}

            <div className="mt-8 border border-foreground/8 bg-secondary/45 px-5 py-4 text-sm text-foreground/52">
              {copy.exportNote}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
