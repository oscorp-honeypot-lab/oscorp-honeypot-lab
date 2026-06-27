import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SessionDetailView } from "./SessionDetailPage";
import type { SessionDetailResponse } from "../../api/generated/types.gen";

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
