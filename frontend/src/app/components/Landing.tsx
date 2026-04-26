import { useEffect, useState } from "react";
import { Link } from "react-router";

import LanguageToggle from "./LanguageToggle";
import { fetchHealth, fetchSummary, type HealthResponse, type YearlyStatistic } from "../lib/api";
import {
  formatCompactPopulation,
  formatInteger,
  formatPercent,
} from "../lib/format";
import { useLanguage } from "../lib/language";

const landingCopy = {
  ru: {
    label: "Демографический обзор",
    heading: "Рабочий контур для анализа территорий и подготовки отчетов",
    text:
      "Интерфейс собирает численность населения, динамику за период и сравнительные таблицы по территориям, а затем переводит их в сценарий аналитики и выгрузки.",
    analytics: "Открыть аналитику",
    report: "Перейти к отчету",
    overview: "Обзор",
    analyticsNav: "Аналитика",
    reportNav: "Отчет",
    dataReady: "Данные доступны",
    dataChecking: "Проверка данных",
    latestYear: "Последний срез",
    population: "Население",
    urbanShare: "Доля городского населения",
    territories: "Территорий в наборе",
    sections: [
      {
        title: "Численность и структура",
        text: "На первом экране видны общий объем населения, доля городских жителей и покрытие по территориям.",
      },
      {
        title: "Сравнение территорий",
        text: "В аналитике доступны фильтры по субъекту, типу территории и периоду анализа, а также сравнительный слой по изменениям населения.",
      },
      {
        title: "Генерация отчета",
        text: "После выбора периода и территории можно перейти к подготовке выгрузки и сформировать комплект файлов.",
      },
    ],
    workflowLabel: "Рабочий сценарий",
    workflowTitle: "Три шага от выбора территории до файла отчета",
    workflow: [
      "Выбрать Россию или конкретный субъект РФ.",
      "Проверить численность населения, динамику и сравнительные таблицы.",
      "Перейти к формированию отчета и выгрузить файлы.",
    ],
    attention: "Сейчас есть проблема с загрузкой данных",
  },
  en: {
    label: "Demographic overview",
    heading: "Working surface for territorial analysis and report preparation",
    text:
      "The interface brings together population size, period dynamics, and comparative territory tables, then turns them into an analytics and export workflow.",
    analytics: "Open analytics",
    report: "Open report",
    overview: "Overview",
    analyticsNav: "Analytics",
    reportNav: "Report",
    dataReady: "Data available",
    dataChecking: "Checking data",
    latestYear: "Latest snapshot",
    population: "Population",
    urbanShare: "Urban share",
    territories: "Territories in dataset",
    sections: [
      {
        title: "Population and structure",
        text: "The opening screen shows total population, urban share, and territory coverage.",
      },
      {
        title: "Territory comparison",
        text: "The analytics view supports subject, territory type, and period filters along with comparative change layers.",
      },
      {
        title: "Report generation",
        text: "After choosing a period and territory, move into report preparation and export the file set.",
      },
    ],
    workflowLabel: "Workflow",
    workflowTitle: "Three steps from territory selection to report files",
    workflow: [
      "Choose Russia or a specific region.",
      "Review population size, trend, and comparison tables.",
      "Move to report preparation and export the files.",
    ],
    attention: "There is currently a data loading issue",
  },
} as const;

export default function Landing() {
  const { language } = useLanguage();
  const copy = landingCopy[language];

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [summary, setSummary] = useState<YearlyStatistic | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const healthPayload = await fetchHealth();
        const years = healthPayload.data.years_available;
        const latestYear = years.at(-1);

        if (!latestYear) {
          throw new Error(
            language === "en"
              ? "No years available in dataset"
              : "В наборе данных отсутствуют доступные годы",
          );
        }

        const summaryPayload = await fetchSummary(latestYear);

        if (!active) {
          return;
        }

        setHealth(healthPayload);
        setSummary(summaryPayload);
      } catch (loadError) {
        if (!active) {
          return;
        }

        setError(loadError instanceof Error ? loadError.message : copy.attention);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      active = false;
    };
  }, [copy.attention, language]);

  const years = health?.data.years_available ?? [];
  const latestYear = summary?.year ?? years.at(-1);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <main className="mx-auto max-w-[1500px] px-4 py-6 sm:px-8 lg:px-12">
        <header className="border-b border-foreground/10 pb-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-foreground/45">
                {copy.label}
              </div>
              <div
                className="mt-2 text-2xl tracking-[-0.05em]"
                style={{ fontFamily: "var(--font-headline)", fontWeight: 800 }}
              >
                Демографика
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <nav className="flex items-center gap-2 text-sm text-foreground/65">
                <a href="#overview" className="border border-foreground/10 px-4 py-2 transition hover:bg-secondary">
                  {copy.overview}
                </a>
                <Link to="/analytics" className="border border-foreground/10 px-4 py-2 transition hover:bg-secondary">
                  {copy.analyticsNav}
                </Link>
                <Link to="/report" className="border border-foreground/10 px-4 py-2 transition hover:bg-secondary">
                  {copy.reportNav}
                </Link>
              </nav>
              <LanguageToggle />
            </div>
          </div>
        </header>

        <section className="mt-6">
          <div className="border border-foreground/10 bg-white p-6 sm:p-8 lg:p-10">
            <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-foreground/45">
              {loading ? copy.dataChecking : copy.dataReady}
            </div>
            <h1
              className="mt-4 max-w-4xl text-4xl leading-[0.95] tracking-[-0.06em] sm:text-5xl lg:text-6xl"
              style={{ fontFamily: "var(--font-headline)", fontWeight: 800 }}
            >
              {copy.heading}
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-7 text-foreground/65">{copy.text}</p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                to="/analytics"
                className="bg-foreground px-5 py-3 text-center text-sm font-semibold text-background transition hover:opacity-92"
              >
                {copy.analytics}
              </Link>
              <Link
                to="/report"
                className="border border-foreground/10 px-5 py-3 text-center text-sm font-semibold text-foreground transition hover:bg-secondary"
              >
                {copy.report}
              </Link>
            </div>

            <div className="mt-10 grid gap-px border border-foreground/10 bg-foreground/10 sm:grid-cols-2 xl:grid-cols-4">
              {[
                {
                  label: copy.latestYear,
                  value: latestYear ?? "—",
                },
                {
                  label: copy.population,
                  value: summary ? formatCompactPopulation(summary.total_population, language) : "—",
                },
                {
                  label: copy.urbanShare,
                  value: summary ? formatPercent(summary.urban_ratio * 100, 1, language) : "—",
                },
                {
                  label: copy.territories,
                  value: summary ? formatInteger(summary.number_of_municipalities, language) : "—",
                },
              ].map((item) => (
                <div key={item.label} className="bg-background px-4 py-5">
                  <div className="text-sm text-foreground/45">{item.label}</div>
                  <div className="mt-2 text-2xl font-semibold tracking-[-0.04em]">{item.value}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="overview" className="mt-6 grid gap-px border border-foreground/10 bg-foreground/10 lg:grid-cols-3">
          {copy.sections.map((item) => (
            <div key={item.title} className="bg-background px-5 py-6">
              <div
                className="text-2xl tracking-[-0.04em]"
                style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
              >
                {item.title}
              </div>
              <p className="mt-4 text-base leading-7 text-foreground/65">{item.text}</p>
            </div>
          ))}
        </section>

        <section className="mt-6 border border-foreground/10 bg-white p-6 sm:p-8">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-foreground/45">
            {copy.workflowLabel}
          </div>
          <h2
            className="mt-3 text-3xl tracking-[-0.05em]"
            style={{ fontFamily: "var(--font-headline)", fontWeight: 700 }}
          >
            {copy.workflowTitle}
          </h2>

          <div className="mt-8 grid gap-4 lg:grid-cols-3">
            {copy.workflow.map((item, index) => (
              <div key={item} className="border border-foreground/10 px-5 py-5">
                <div className="text-sm font-semibold uppercase tracking-[0.2em] text-foreground/42">
                  {String(index + 1).padStart(2, "0")}
                </div>
                <p className="mt-4 text-base leading-7 text-foreground/70">{item}</p>
              </div>
            ))}
          </div>

          {error ? (
            <div className="mt-6 border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              {copy.attention}: {error}
            </div>
          ) : null}
        </section>
      </main>
    </div>
  );
}
