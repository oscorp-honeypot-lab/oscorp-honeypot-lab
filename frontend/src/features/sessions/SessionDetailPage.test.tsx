import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { SessionDetailPage, SessionDetailView } from "./SessionDetailPage";
import type {
  SessionDetailResponse,
  SessionListItemResponse,
  SessionPageResponse,
} from "../../api/generated/types.gen";

vi.mock("../../api/client", async () => {
  const actual = await vi.importActual<typeof import("../../api/client")>(
    "../../api/client",
  );
  return {
    ...actual,
    getSessionDetail: vi.fn(),
    reviewSession: vi.fn(),
  };
});

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { id: "u1", username: "analyst1", role: "analyst" },
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    loginPending: false,
    loginError: false,
  }),
}));

const baseSession = {
  session_key: "test-sensor:abc123",
  session_id: "abc123",
  sensor: "test-sensor",
  src_ip: "203.0.113.10",
  src_port: 45123,
  first_event_at: "2026-06-25T18:00:00Z",
  last_event_at: "2026-06-25T18:01:30Z",
  duration_seconds: 90,
  lifecycle_status: "complete",
  event_count: 3,
  command_count: 1,
  download_count: 1,
  username: "root",
  has_successful_login: true,
  country: "Argentina",
  risk_score: 75,
  risk_level: "high",
  reviewed: false,
  reviewed_at: null,
  reviewed_by: null,
  reviewed_by_username: null,
  source_mode: "lab",
};

const baseData: SessionDetailResponse = {
  session: baseSession,
  score: {
    score: 75,
    level: "high",
    reasons: [{ rule_id: "login_success", weight: 30, evidence: ["cowrie.login.success"] }],
    rules_version: "1.0.0",
    calculated_at: "2026-06-25T18:02:00Z",
  },
  commands: ["whoami", "cat /etc/passwd"],
  downloads: [
    {
      timestamp: "2026-06-25T18:01:00Z",
      url: "http://payload-server/bot.sh",
      sha256: "deadbeef",
    },
  ],
  events: [
    {
      id: 1,
      timestamp: "2026-06-25T18:00:00Z",
      event_type: "cowrie.session.connect",
      session_id: "abc123",
      sensor: "test-sensor",
      src_ip: "203.0.113.10",
      src_port: 45123,
      username: null,
      command: null,
      url: null,
      sha256: null,
      country: null,
    },
  ],
};

const noop = () => undefined;

describe("SessionDetailView states", () => {
  it("announces the loading state", () => {
    render(
      <SessionDetailView
        loading
        notFound={false}
        error={false}
        data={undefined}
        reviewing={false}
        canReview={false}
        onReview={noop}
        onRetry={noop}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Cargando sesión");
  });

  it("shows a not-found message for missing sessions", () => {
    render(
      <SessionDetailView
        loading={false}
        notFound
        error={false}
        data={undefined}
        reviewing={false}
        canReview={false}
        onReview={noop}
        onRetry={noop}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Sesión no encontrada");
  });

  it("shows an error state with retry option", () => {
    const retry = vi.fn();
    render(
      <SessionDetailView
        loading={false}
        notFound={false}
        error
        data={undefined}
        reviewing={false}
        canReview={false}
        onReview={noop}
        onRetry={retry}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(retry).toHaveBeenCalledOnce();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("renders session metadata when data is available", () => {
    render(
      <SessionDetailView
        loading={false}
        notFound={false}
        error={false}
        data={baseData}
        reviewing={false}
        canReview={true}
        onReview={noop}
        onRetry={noop}
      />,
    );
    expect(screen.getByText("203.0.113.10")).toBeInTheDocument();
    expect(screen.getByText("whoami")).toBeInTheDocument();
    expect(screen.getByText("http://payload-server/bot.sh")).toBeInTheDocument();
    expect(screen.getByText("75")).toBeInTheDocument();
  });

  it("shows mark-as-reviewed button for unreviewed sessions", () => {
    render(
      <SessionDetailView
        loading={false}
        notFound={false}
        error={false}
        data={baseData}
        reviewing={false}
        canReview={true}
        onReview={noop}
        onRetry={noop}
      />,
    );
    expect(
      screen.getByRole("button", { name: /marcar como revisada/i }),
    ).toBeInTheDocument();
  });

  it("shows clear-review button for already-reviewed sessions", () => {
    const reviewedData: SessionDetailResponse = {
      ...baseData,
      session: {
        ...baseSession,
        reviewed: true,
        reviewed_by_username: "analyst1",
        reviewed_at: "2026-06-25T19:00:00Z",
      },
    };
    render(
      <SessionDetailView
        loading={false}
        notFound={false}
        error={false}
        data={reviewedData}
        reviewing={false}
        canReview={true}
        onReview={noop}
        onRetry={noop}
      />,
    );
    expect(
      screen.getByRole("button", { name: /quitar revisión/i }),
    ).toBeInTheDocument();
  });

  it("calls onReview with the toggled value when review button is clicked", () => {
    const onReview = vi.fn();
    render(
      <SessionDetailView
        loading={false}
        notFound={false}
        error={false}
        data={baseData}
        reviewing={false}
        canReview={true}
        onReview={onReview}
        onRetry={noop}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /marcar como revisada/i }));
    expect(onReview).toHaveBeenCalledWith(true);
  });
});

describe("SessionDetailPage container — optimistic review update", () => {
  it("patches the sessions list cache before the mutation resolves, and reconciles after", async () => {
    const { getSessionDetail, reviewSession } = await import("../../api/client");
    const sessionKey = baseSession.session_key;

    let resolveReview: (value: SessionListItemResponse) => void = () => undefined;
    const reviewPromise = new Promise<SessionListItemResponse>((resolve) => {
      resolveReview = resolve;
    });
    vi.mocked(reviewSession).mockReturnValue(reviewPromise);
    vi.mocked(getSessionDetail).mockResolvedValue(baseData);

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const listQueryKey = ["sessions", { page: 1, pageSize: 25 }] as const;
    const listData: SessionPageResponse = {
      items: [baseSession],
      pagination: { page: 1, page_size: 25, total: 1, pages: 1 },
    };
    queryClient.setQueryData(listQueryKey, listData);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/sessions/${sessionKey}`]}>
          <Routes>
            <Route path="/sessions/:sessionKey" element={<SessionDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: /marcar como revisada/i }),
    );

    await waitFor(() => {
      const list = queryClient.getQueryData<SessionPageResponse>(listQueryKey);
      expect(list?.items[0].reviewed).toBe(true);
    });
    expect(vi.mocked(reviewSession)).toHaveBeenCalledWith(sessionKey, true);

    resolveReview({
      ...baseSession,
      reviewed: true,
      reviewed_by_username: "analyst1",
      reviewed_at: "2026-07-02T12:00:00Z",
    });

    await waitFor(() => {
      const list = queryClient.getQueryData<SessionPageResponse>(listQueryKey);
      expect(list?.items[0].reviewed_by_username).toBe("analyst1");
    });
  });
});
