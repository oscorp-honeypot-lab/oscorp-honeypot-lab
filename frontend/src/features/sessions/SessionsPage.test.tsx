import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SessionsTable } from "./SessionsPage";

const tableStub = null as never;

describe("SessionsTable states", () => {
  it("announces the loading state", () => {
    render(
      <SessionsTable
        table={tableStub}
        loading
        error={false}
        empty={false}
        refreshing={false}
        onRetry={() => undefined}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Cargando sesiones");
  });

  it("shows an accessible empty state", () => {
    render(
      <SessionsTable
        table={tableStub}
        loading={false}
        error={false}
        empty
        refreshing={false}
        onRetry={() => undefined}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "No hay sesiones para estos filtros",
    );
  });

  it("allows retrying after an error", () => {
    const retry = vi.fn();
    render(
      <SessionsTable
        table={tableStub}
        loading={false}
        error
        empty={false}
        refreshing={false}
        onRetry={retry}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(retry).toHaveBeenCalledOnce();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
