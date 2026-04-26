import type { MunicipalityData, TrendAnalysis, YearlyStatistic } from "./api";

export interface SeriesPoint {
  year: number;
  totalPopulation: number;
  urbanPopulation: number;
  ruralPopulation: number;
  urbanRatio: number;
}

export interface ForecastPoint {
  forecastYear: number;
  population: number;
  absoluteChange: number;
  percentChange: number;
  urbanRatio: number;
}

export interface TerritoryInsights {
  label: string;
  start: SeriesPoint;
  end: SeriesPoint;
  absoluteChange: number;
  percentChange: number;
  urbanChange: number;
  ruralChange: number;
  urbanRatioChangePp: number;
  averageAnnualChange: number;
  recentNote: string;
  summaryParagraphs: string[];
  trendParagraphs: string[];
  forecastParagraphs: string[];
  recommendations: string[];
  forecastFive: ForecastPoint;
  forecastTen: ForecastPoint;
}

export function buildYearRange(startYear: number, endYear: number) {
  return Array.from({ length: endYear - startYear + 1 }, (_, index) => startYear + index);
}

export function toSeriesPoint(
  point: MunicipalityData | YearlyStatistic,
): SeriesPoint {
  return {
    year: point.year,
    totalPopulation: point.total_population,
    urbanPopulation: point.urban_population,
    ruralPopulation: point.rural_population,
    urbanRatio: point.urban_ratio,
  };
}

export function buildSeriesFromTrend(trend: TrendAnalysis): SeriesPoint[] {
  return trend.years.map((year, index) => ({
    year,
    totalPopulation: trend.total_population[index],
    urbanPopulation: trend.urban_population[index],
    ruralPopulation: trend.rural_population[index],
    urbanRatio:
      trend.total_population[index] > 0
        ? trend.urban_population[index] / trend.total_population[index]
        : 0,
  }));
}

function averageAnnualDelta(
  series: SeriesPoint[],
  selector: (point: SeriesPoint) => number,
  recentYears?: number,
) {
  if (series.length < 2) {
    return 0;
  }

  const start =
    recentYears == null
      ? series[0]
      : series[Math.max(0, series.length - (recentYears + 1))];
  const end = series.at(-1)!;
  const span = end.year - start.year;

  if (span <= 0) {
    return 0;
  }

  return (selector(end) - selector(start)) / span;
}

function populationChangeVerb(value: number) {
  if (value > 0) return "выросла";
  if (value < 0) return "сократилась";
  return "почти не изменилась";
}

function trendNoun(value: number) {
  if (value > 0) return "рост";
  if (value < 0) return "снижение";
  return "стабилизация";
}

function buildRecentDynamicsNote(overall: number, recent: number) {
  if (Math.abs(overall) < 1 && Math.abs(recent) < 1) {
    return "Динамика последних лет близка к стабилизации.";
  }
  if (overall <= 0 && recent > 0) {
    return "В последние годы наблюдается локальная стабилизация и переход к росту.";
  }
  if (overall >= 0 && recent < 0) {
    return "В последние годы положительная динамика ослабла и сменилась снижением.";
  }

  const ratio = Math.abs(recent) / Math.max(Math.abs(overall), 1);
  if (ratio > 1.15) {
    return recent > 0
      ? "В последние годы темп роста ускорился."
      : "В последние годы темп снижения ускорился.";
  }
  if (ratio < 0.85) {
    return recent > 0
      ? "В последние годы темп роста замедлился."
      : "В последние годы темп снижения замедлился.";
  }

  return "Динамика последних лет в целом соответствует среднему темпу рассматриваемого периода.";
}

function buildForecastPoint(series: SeriesPoint[], yearsAhead: number): ForecastPoint {
  const overallPopulationDelta = averageAnnualDelta(series, (point) => point.totalPopulation);
  const recentPopulationDelta = averageAnnualDelta(
    series,
    (point) => point.totalPopulation,
    3,
  );
  const overallRatioDelta = averageAnnualDelta(series, (point) => point.urbanRatio);
  const recentRatioDelta = averageAnnualDelta(series, (point) => point.urbanRatio, 3);

  const annualPopulationDelta =
    series.length >= 4
      ? (overallPopulationDelta + recentPopulationDelta) / 2
      : overallPopulationDelta;
  const annualRatioDelta =
    series.length >= 4 ? (overallRatioDelta + recentRatioDelta) / 2 : overallRatioDelta;

  const end = series.at(-1)!;
  const population = Math.max(0, Math.round(end.totalPopulation + annualPopulationDelta * yearsAhead));
  const urbanRatio = Math.min(1, Math.max(0, end.urbanRatio + annualRatioDelta * yearsAhead));
  const absoluteChange = population - end.totalPopulation;

  return {
    forecastYear: end.year + yearsAhead,
    population,
    absoluteChange,
    percentChange: end.totalPopulation > 0 ? (absoluteChange / end.totalPopulation) * 100 : 0,
    urbanRatio,
  };
}

function buildFactorParagraph(
  absoluteChange: number,
  urbanRatioChangePp: number,
  urbanChange: number,
  ruralChange: number,
) {
  if (absoluteChange < 0 && urbanRatioChangePp > 0.3) {
    return "Снижение общей численности при росте доли городских жителей может указывать на концентрацию населения в крупных центрах и ослабление периферийных территорий.";
  }
  if (absoluteChange > 0 && urbanRatioChangePp > 0.3) {
    return "Рост численности вместе с повышением доли городских жителей обычно связан с агломерационным эффектом, миграционной привлекательностью и расширением городских рынков труда.";
  }
  if (absoluteChange < 0 && urbanChange < 0 && ruralChange < 0) {
    return "Одновременное снижение городского и сельского населения говорит о более широком демографическом сжатии, где вероятными факторами выступают естественная убыль и недостаточный миграционный приток.";
  }
  if (ruralChange < 0 && urbanChange >= 0) {
    return "Сокращение сельского населения при более устойчивой городской динамике показывает внутреннюю концентрацию жителей вокруг опорных центров.";
  }
  if (absoluteChange > 0) {
    return "Текущая динамика указывает на относительно благоприятную траекторию, где вероятными факторами выступают миграционный приток, занятость и качество городской среды.";
  }
  return "По одной только численности населения нельзя окончательно объяснить причину изменений; для уточнения картины нужны данные о миграции, рождаемости, смертности и занятости.";
}

function buildRecommendations(
  absoluteChange: number,
  urbanRatioChangePp: number,
  ruralChange: number,
) {
  const recommendations: string[] = [];

  if (absoluteChange < 0) {
    recommendations.push(
      "Сфокусировать социальную политику на удержании населения: доступности рабочих мест, первичного здравоохранения и поддержке семей с детьми.",
    );
  } else {
    recommendations.push(
      "Синхронизировать развитие социальной инфраструктуры с зонами роста населения, чтобы заранее расширять мощности школ, детских садов, поликлиник и жилья.",
    );
  }

  if (ruralChange < 0) {
    recommendations.push(
      "Укреплять опорные населенные пункты, транспортную связность и мобильные социальные сервисы для периферийных и сельских территорий.",
    );
  } else {
    recommendations.push(
      "Поддерживать сбалансированную сеть услуг между городскими и внегородскими территориями, чтобы не перегружать отдельные центры роста.",
    );
  }

  if (urbanRatioChangePp > 0.3) {
    recommendations.push(
      "Резервировать мощности транспорта, инженерной инфраструктуры и земли под развитие городских и пригородных зон.",
    );
  } else {
    recommendations.push(
      "Сохранять качество среды в существующей сети поселений без распыления инвестиций на избыточные площадки развития.",
    );
  }

  recommendations.push(
    "Дополнить мониторинг данными о миграции, рождаемости, смертности и занятости, чтобы уточнять меры поддержки и территориальные решения.",
  );

  return recommendations;
}

export function buildInsights(
  label: string,
  series: SeriesPoint[],
  nationalSeries?: SeriesPoint[],
): TerritoryInsights | null {
  if (series.length < 2) {
    return null;
  }

  const start = series[0];
  const end = series.at(-1)!;
  const absoluteChange = end.totalPopulation - start.totalPopulation;
  const percentChange =
    start.totalPopulation > 0 ? (absoluteChange / start.totalPopulation) * 100 : 0;
  const urbanChange = end.urbanPopulation - start.urbanPopulation;
  const ruralChange = end.ruralPopulation - start.ruralPopulation;
  const urbanRatioChangePp = (end.urbanRatio - start.urbanRatio) * 100;
  const averageAnnualChange = averageAnnualDelta(series, (point) => point.totalPopulation);
  const recentAnnualChange = averageAnnualDelta(
    series,
    (point) => point.totalPopulation,
    3,
  );
  const forecastFive = buildForecastPoint(series, 5);
  const forecastTen = buildForecastPoint(series, 10);
  const recentNote = buildRecentDynamicsNote(averageAnnualChange, recentAnnualChange);

  let comparisonText = "";
  if (nationalSeries && nationalSeries.length >= 2) {
    const nationalStart = nationalSeries[0];
    const nationalEnd = nationalSeries.at(-1)!;
    const nationalChange =
      nationalStart.totalPopulation > 0
        ? ((nationalEnd.totalPopulation - nationalStart.totalPopulation) /
            nationalStart.totalPopulation) *
          100
        : 0;
    const delta = percentChange - nationalChange;

    if (Math.abs(delta) < 1) {
      comparisonText = "Динамика территории близка к общероссийской.";
    } else if (delta > 0) {
      comparisonText = `Динамика территории лучше общероссийской на ${delta.toLocaleString("ru-RU", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })} п.п.`;
    } else {
      comparisonText = `Динамика территории слабее общероссийской на ${Math.abs(delta).toLocaleString("ru-RU", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })} п.п.`;
    }
  }

  return {
    label,
    start,
    end,
    absoluteChange,
    percentChange,
    urbanChange,
    ruralChange,
    urbanRatioChangePp,
    averageAnnualChange,
    recentNote,
    forecastFive,
    forecastTen,
    summaryParagraphs: [
      `За ${start.year}-${end.year} гг. численность населения ${label} ${populationChangeVerb(absoluteChange)} с ${start.totalPopulation.toLocaleString("ru-RU")} до ${end.totalPopulation.toLocaleString("ru-RU")} человек.`,
      `Изменение за период составило ${absoluteChange > 0 ? "+" : ""}${absoluteChange.toLocaleString("ru-RU")} человек (${percentChange.toLocaleString("ru-RU", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      })}%). На ${end.year} год доля городского населения равна ${(end.urbanRatio * 100).toLocaleString("ru-RU", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      })}%.`,
      recentNote,
    ],
    trendParagraphs: [
      `Базовый тренд периода — ${trendNoun(absoluteChange)} численности населения при ${urbanRatioChangePp > 0 ? "росте доли" : urbanRatioChangePp < 0 ? "снижении доли" : "стабильной доле"} городских жителей.`,
      comparisonText || "Текущая динамика оценивается по временным рядам численности населения и структуре расселения.",
      buildFactorParagraph(absoluteChange, urbanRatioChangePp, urbanChange, ruralChange),
    ],
    forecastParagraphs: [
      "Прогноз носит ориентировочный характер и построен методом линейной экстраполяции по средней и недавней годовой динамике.",
      `При сохранении текущей траектории численность населения может составить около ${forecastFive.population.toLocaleString("ru-RU")} человек к ${forecastFive.forecastYear} году и ${forecastTen.population.toLocaleString("ru-RU")} человек к ${forecastTen.forecastYear} году.`,
    ],
    recommendations: buildRecommendations(absoluteChange, urbanRatioChangePp, ruralChange),
  };
}
