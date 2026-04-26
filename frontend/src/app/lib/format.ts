type FormatLanguage = "ru" | "en";

function resolveLocale(language: FormatLanguage) {
  return language === "en" ? "en-US" : "ru-RU";
}

export function formatInteger(value: number, language: FormatLanguage = "ru") {
  return new Intl.NumberFormat(resolveLocale(language)).format(Math.round(value));
}

export function formatSignedInteger(value: number, language: FormatLanguage = "ru") {
  return `${value > 0 ? "+" : ""}${formatInteger(value, language)}`;
}

export function formatPercent(value: number, digits = 1, language: FormatLanguage = "ru") {
  return `${value.toLocaleString(resolveLocale(language), {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}%`;
}

export function formatPoints(value: number, digits = 2, language: FormatLanguage = "ru") {
  const suffix = language === "en" ? "pp" : "п.п.";
  return `${value > 0 ? "+" : ""}${value.toLocaleString(resolveLocale(language), {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })} ${suffix}`;
}

export function formatCompactPopulation(value: number, language: FormatLanguage = "ru") {
  const locale = resolveLocale(language);
  const absValue = Math.abs(value);
  if (absValue >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString(locale, {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })} ${language === "en" ? "M" : "млн"}`;
  }

  if (absValue >= 1_000) {
    return `${(value / 1_000).toLocaleString(locale, {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })} ${language === "en" ? "K" : "тыс"}`;
  }

  return formatInteger(value, language);
}

export function formatDateTime(value: string, language: FormatLanguage = "ru") {
  return new Date(value).toLocaleString(resolveLocale(language), {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatFileSize(bytes: number, language: FormatLanguage = "ru") {
  const locale = resolveLocale(language);
  if (bytes >= 1_000_000) {
    return `${(bytes / 1_000_000).toLocaleString(locale, {
      maximumFractionDigits: 1,
    })} ${language === "en" ? "MB" : "МБ"}`;
  }
  if (bytes >= 1_000) {
    return `${(bytes / 1_000).toLocaleString(locale, {
      maximumFractionDigits: 1,
    })} ${language === "en" ? "KB" : "КБ"}`;
  }
  return `${bytes} ${language === "en" ? "B" : "Б"}`;
}
