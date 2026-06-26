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
