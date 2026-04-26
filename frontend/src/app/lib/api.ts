export type Scope = "russia" | "region";

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  data: {
    years_available: number[];
    total_records: number;
  };
  llama: {
    available: boolean;
    host: string;
    default_model: string;
  };
}

export interface MunicipalityData {
  code: string;
  name: string;
  total_population: number;
  urban_population: number;
  rural_population: number;
  urban_ratio: number;
  year: number;
}

export interface YearlyStatistic {
  year: number;
  total_population: number;
  urban_population: number;
  rural_population: number;
  urban_ratio: number;
  number_of_municipalities: number;
}

export interface TrendAnalysis {
  years: number[];
  total_population: number[];
  urban_population: number[];
  rural_population: number[];
  growth_rate: number;
  average_urban_ratio: number;
}

export interface GrowthDeclineItem {
  name: string;
  start_population: number;
  end_population: number;
  absolute_change: number;
  percent_change: number;
}

export interface GrowthDeclineResponse {
  start_year: number;
  end_year: number;
  growth: GrowthDeclineItem[];
  decline: GrowthDeclineItem[];
}

export interface GeneratedReportFile {
  format: "docx" | "pdf" | "both";
  filename: string;
  download_url: string;
  content_type: string;
  size_bytes: number;
}

export interface ReportGenerationResponse {
  report_id: string;
  title: string;
  scope: Scope;
  start_year: number;
  end_year: number;
  created_at: string;
  files: GeneratedReportFile[];
}

export interface ReportGenerationPayload {
  start_year: number;
  end_year: number;
  scope: Scope;
  region_name?: string;
  format: "docx" | "pdf" | "both";
  focus_prompt?: string;
  include_ai_summary: boolean;
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");
const API_ORIGIN = API_BASE.replace(/\/api\/v1$/, "");

async function parseError(response: Response) {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    return JSON.stringify(payload);
  } catch {
    return response.statusText || "Request failed";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json() as Promise<T>;
}

export async function fetchHealth() {
  return request<HealthResponse>("/health");
}

export async function fetchYears() {
  return request<{ years: number[]; count: number }>("/data/years");
}

export async function fetchSummary(year: number) {
  return request<YearlyStatistic>(`/data/summary/${year}`);
}

export async function fetchTrends(startYear: number, endYear: number) {
  return request<TrendAnalysis>(
    `/data/trends?start_year=${startYear}&end_year=${endYear}`,
  );
}

export async function fetchRegions(year: number) {
  return request<{ year: number; regions: MunicipalityData[]; count: number }>(
    `/data/regions/${year}`,
  );
}

export async function fetchMunicipality(code: string, year: number) {
  return request<MunicipalityData>(`/data/municipality/${encodeURIComponent(code)}?year=${year}`);
}

export async function searchTerritories(query: string, year: number, limit = 8) {
  return request<{ results: MunicipalityData[]; count: number }>(
    `/data/search?query=${encodeURIComponent(query)}&year=${year}&limit=${limit}`,
  );
}

export async function fetchGrowthDecline(
  startYear: number,
  endYear: number,
  limit = 6,
) {
  return request<GrowthDeclineResponse>(
    `/trends/growth-decline?start_year=${startYear}&end_year=${endYear}&limit=${limit}`,
  );
}

export async function fetchTerritorySeries(code: string, years: number[]) {
  const responses = await Promise.all(
    years.map(async (year) => {
      try {
        return await fetchMunicipality(code, year);
      } catch {
        return null;
      }
    }),
  );

  return responses.filter(Boolean) as MunicipalityData[];
}

export async function generateReport(payload: ReportGenerationPayload) {
  return request<ReportGenerationResponse>("/reports/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function resolveDownloadUrl(path: string) {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  if (path.startsWith("/")) {
    return `${API_ORIGIN}${path}`;
  }
  return `${API_BASE}/${path}`;
}
