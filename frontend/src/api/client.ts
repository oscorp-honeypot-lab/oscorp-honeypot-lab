import {
  loginApiV1AuthLoginPost,
  logoutApiV1AuthLogoutPost,
  meApiV1AuthMeGet,
  summaryApiV1AnalyticsSummaryGet,
  timelineApiV1AnalyticsTimelineGet,
} from "./generated/sdk.gen";
import { client } from "./generated/client.gen";
import type {
  AnalyticsSummaryResponse,
  LoginRequestWritable,
  TimelineResponse,
  UserResponse,
} from "./generated/types.gen";

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
