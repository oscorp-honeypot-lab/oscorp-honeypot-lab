import {
  geoStatsApiV1AnalyticsGeoStatsGet,
  loginApiV1AuthLoginPost,
  logoutApiV1AuthLogoutPost,
  meApiV1AuthMeGet,
  mttdStatsApiV1AnalyticsMttdGet,
  reviewSessionApiV1SessionsSessionKeyReviewPatch,
  sessionDetailApiV1SessionsSessionKeyGet,
  sessionsApiV1SessionsGet,
  summaryApiV1AnalyticsSummaryGet,
  timelineApiV1AnalyticsTimelineGet,
} from "./generated/sdk.gen";
import { client } from "./generated/client.gen";
import type {
  AnalyticsSummaryResponse,
  GeoStatsResponse,
  LoginRequestWritable,
  MttdStatsResponse,
  SessionDetailResponse,
  SessionListItemResponse,
  SessionPageResponse,
  TimelineResponse,
  UserResponse,
} from "./generated/types.gen";

export type SessionSortField =
  | "last_event_at"
  | "risk_score"
  | "event_count"
  | "command_count"
  | "download_count"
  | "src_ip"
  | "country";

export type SessionQuery = {
  page: number;
  pageSize: number;
  srcIp?: string;
  country?: string;
  username?: string;
  riskLevel?: string;
  reviewed?: boolean;
  sortBy: SessionSortField;
  sortOrder: "asc" | "desc";
};

export type ReportPeriodType = "daily" | "weekly";
export type ReportFormat = "html" | "csv";

export type LabRunResponse = {
  id: number;
  scenario: string;
  status: string;
  actor: string;
  started_at: string;
  finished_at: string | null;
  exit_code: number | null;
  log_text: string | null;
  error_detail: string | null;
  pipeline_events_read: number | null;
  pipeline_errors: number | null;
};

export type ReportDeliveryResponse = {
  id: string;
  report_id: string;
  channel: string;
  format: string;
  status: string;
  filename: string | null;
  error_code: string | null;
};

client.setConfig({
  baseUrl: "",
  credentials: "include",
});

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
  }
}

function unwrap<T>(result: {
  data?: T;
  error?: unknown;
  response?: Response;
}): T {
  if (result.data !== undefined) {
    return result.data;
  }
  throw new ApiError("api_request_failed", result.response?.status);
}

export async function getCurrentUser(): Promise<UserResponse> {
  return unwrap(await meApiV1AuthMeGet());
}

export async function login(
  credentials: LoginRequestWritable,
): Promise<UserResponse> {
  const result = unwrap(
    await loginApiV1AuthLoginPost({ body: credentials }),
  );
  return result.user;
}

function csrfToken(): string {
  const prefix = "oscorp_csrf=";
  const cookie = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : "";
}

export async function logout(): Promise<void> {
  unwrap(
    await logoutApiV1AuthLogoutPost({
      headers: { "X-CSRF-Token": csrfToken() },
    }),
  );
}

export async function getSummary(): Promise<AnalyticsSummaryResponse> {
  return unwrap(await summaryApiV1AnalyticsSummaryGet());
}

export async function getTimeline(hours: number): Promise<TimelineResponse> {
  return unwrap(
    await timelineApiV1AnalyticsTimelineGet({
      query: { hours },
    }),
  );
}

export async function getSessionDetail(
  sessionKey: string,
): Promise<SessionDetailResponse> {
  return unwrap(
    await sessionDetailApiV1SessionsSessionKeyGet({
      path: { session_key: sessionKey },
    }),
  );
}

export async function reviewSession(
  sessionKey: string,
  reviewed: boolean,
): Promise<SessionListItemResponse> {
  return unwrap(
    await reviewSessionApiV1SessionsSessionKeyReviewPatch({
      path: { session_key: sessionKey },
      body: { reviewed },
      headers: { "X-CSRF-Token": csrfToken() },
    }),
  );
}

export async function getMttdStats(): Promise<MttdStatsResponse> {
  return unwrap(await mttdStatsApiV1AnalyticsMttdGet());
}

export async function getGeoStats(): Promise<GeoStatsResponse> {
  return unwrap(await geoStatsApiV1AnalyticsGeoStatsGet());
}

export async function getSessions(
  query: SessionQuery,
): Promise<SessionPageResponse> {
  return unwrap(
    await sessionsApiV1SessionsGet({
      query: {
        page: query.page,
        page_size: query.pageSize,
        src_ip: query.srcIp || undefined,
        country: query.country || undefined,
        username: query.username || undefined,
        risk_level: query.riskLevel || undefined,
        reviewed: query.reviewed,
        sort_by: query.sortBy,
        sort_order: query.sortOrder,
      },
    }),
  );
}

function filenameFromDisposition(header: string | null, fallback: string): string {
  const match = header?.match(/filename="([^"]+)"/);
  return match ? match[1] : fallback;
}

export async function downloadLatestReport(
  periodType: ReportPeriodType,
  format: ReportFormat,
): Promise<void> {
  const response = await fetch(
    `/api/v1/reports/latest/${periodType}/download?format=${format}`,
    { credentials: "include" },
  );
  if (!response.ok) {
    throw new ApiError("report_download_failed", response.status);
  }
  const blob = await response.blob();
  const fallback = `oscorp-report-${periodType}.${format}`;
  const filename = filenameFromDisposition(
    response.headers.get("content-disposition"),
    fallback,
  );
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function sendLatestReportTelegram(
  periodType: ReportPeriodType,
  format: ReportFormat,
): Promise<ReportDeliveryResponse> {
  const response = await fetch(
    `/api/v1/reports/latest/${periodType}/telegram?format=${format}`,
    {
      method: "POST",
      credentials: "include",
      headers: { "X-CSRF-Token": csrfToken() },
    },
  );
  if (!response.ok) {
    throw new ApiError("report_telegram_failed", response.status);
  }
  return (await response.json()) as ReportDeliveryResponse;
}

export async function getLabStatus(): Promise<LabRunResponse | null> {
  const response = await fetch("/api/v1/lab/status", {
    credentials: "include",
  });
  if (response.status === 204) {
    return null;
  }
  if (!response.ok) {
    throw new ApiError("lab_status_failed", response.status);
  }
  return (await response.json()) as LabRunResponse;
}

export async function startLabRun(scenario: string): Promise<LabRunResponse> {
  const response = await fetch("/api/v1/lab/run", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken(),
    },
    body: JSON.stringify({ scenario }),
  });
  if (!response.ok) {
    throw new ApiError("lab_run_failed", response.status);
  }
  return (await response.json()) as LabRunResponse;
}
