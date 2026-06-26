import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LabView } from "./LabView";

const noop = () => undefined;

const SCENARIOS = [
  { key: "brute-force", label: "Fuerza bruta" },
  { key: "recon", label: "Reconocimiento" },
  { key: "malware-download", label: "Descarga malware" },
  { key: "full", label: "Ataque completo" },
];

describe("LabView", () => {
  it("renders buttons for all 4 scenarios", () => {
    render(
      <LabView
        status={null}
        loading={false}
        error={false}
        canRun={true}
        onRun={noop}
        onRetry={noop}
      />,
    );
    expect(screen.getByRole("button", { name: /fuerza bruta/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reconocimiento/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /descarga malware/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ataque completo/i })).toBeInTheDocument();
  });

  it("disables buttons when status is running", () => {
    render(
      <LabView
        status={{ id: 1, scenario: "brute-force", status: "running", actor: "admin", started_at: "", finished_at: null, exit_code: null, log_text: null, error_detail: null, pipeline_events_read: null, pipeline_errors: null }}
        loading={false}
        error={false}
        canRun={true}
        onRun={noop}
        onRetry={noop}
      />,
    );
    for (const s of SCENARIOS) {
      expect(screen.getByRole("button", { name: new RegExp(s.label, "i") })).toBeDisabled();
    }
  });

  it("disables buttons when status is queued", () => {
    render(
      <LabView
        status={{ id: 1, scenario: "recon", status: "queued", actor: "admin", started_at: "", finished_at: null, exit_code: null, log_text: null, error_detail: null, pipeline_events_read: null, pipeline_errors: null }}
        loading={false}
        error={false}
        canRun={true}
        onRun={noop}
        onRetry={noop}
      />,
    );
    expect(screen.getByRole("button", { name: /fuerza bruta/i })).toBeDisabled();
  });

  it("disables buttons when canRun is false (viewer role)", () => {
    render(
      <LabView
        status={null}
        loading={false}
        error={false}
        canRun={false}
        onRun={noop}
        onRetry={noop}
      />,
    );
    for (const s of SCENARIOS) {
      expect(screen.getByRole("button", { name: new RegExp(s.label, "i") })).toBeDisabled();
    }
  });

  it("shows log text in terminal area when available", () => {
    const logText = "[lab] iniciando escenario full\n[attacker-sim] ejecutando...";
    render(
      <LabView
        status={{ id: 2, scenario: "full", status: "completed", actor: "admin", started_at: "", finished_at: null, exit_code: 0, log_text: logText, error_detail: null, pipeline_events_read: 42, pipeline_errors: 0 }}
        loading={false}
        error={false}
        canRun={true}
        onRun={noop}
        onRetry={noop}
      />,
    );
    expect(screen.getByText(/\[lab\] iniciando escenario full/)).toBeInTheDocument();
    expect(screen.getByText(/\[attacker-sim\] ejecutando\.\.\./)).toBeInTheDocument();
  });

  it("shows correct status badge for running", () => {
    render(
      <LabView
        status={{ id: 1, scenario: "brute-force", status: "running", actor: "admin", started_at: "", finished_at: null, exit_code: null, log_text: null, error_detail: null, pipeline_events_read: null, pipeline_errors: null }}
        loading={false}
        error={false}
        canRun={true}
        onRun={noop}
        onRetry={noop}
      />,
    );
    expect(screen.getByText("running")).toBeInTheDocument();
  });

  it("shows correct status badge for completed", () => {
    render(
      <LabView
        status={{ id: 1, scenario: "full", status: "completed", actor: "admin", started_at: "", finished_at: null, exit_code: 0, log_text: null, error_detail: null, pipeline_events_read: 10, pipeline_errors: 0 }}
        loading={false}
        error={false}
        canRun={true}
        onRun={noop}
        onRetry={noop}
      />,
    );
    expect(screen.getByText("completed")).toBeInTheDocument();
  });

  it("calls onRun with the correct scenario key when a button is clicked", () => {
    const onRun = vi.fn();
    render(
      <LabView
        status={null}
        loading={false}
        error={false}
        canRun={true}
        onRun={onRun}
        onRetry={noop}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /reconocimiento/i }));
    expect(onRun).toHaveBeenCalledWith("recon");
  });

  it("shows an error state with retry option", () => {
    const retry = vi.fn();
    render(
      <LabView
        status={null}
        loading={false}
        error
        canRun={false}
        onRun={noop}
        onRetry={retry}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(retry).toHaveBeenCalledOnce();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    render(
      <LabView
        status={null}
        loading
        error={false}
        canRun={false}
        onRun={noop}
        onRetry={noop}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Cargando laboratorio");
  });

  it("enables buttons when status is completed", () => {
    render(
      <LabView
        status={{ id: 1, scenario: "full", status: "completed", actor: "admin", started_at: "", finished_at: null, exit_code: 0, log_text: null, error_detail: null, pipeline_events_read: 10, pipeline_errors: 0 }}
        loading={false}
        error={false}
        canRun={true}
        onRun={noop}
        onRetry={noop}
      />,
    );
    expect(screen.getByRole("button", { name: /fuerza bruta/i })).not.toBeDisabled();
  });
});
