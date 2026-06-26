import type { LabRunResponse } from "../../api/client";

const SCENARIOS: { key: string; label: string }[] = [
  { key: "brute-force", label: "Fuerza bruta" },
  { key: "recon", label: "Reconocimiento" },
  { key: "malware-download", label: "Descarga malware" },
  { key: "full", label: "Ataque completo" },
];

const ACTIVE_STATUSES = new Set(["queued", "running", "processing"]);

const STATUS_STYLE: Record<string, string> = {
  queued: "lab-badge lab-badge--queued",
  running: "lab-badge lab-badge--running",
  processing: "lab-badge lab-badge--processing",
  completed: "lab-badge lab-badge--completed",
  failed: "lab-badge lab-badge--failed",
};

export type LabViewProps = {
  status: LabRunResponse | null;
  loading: boolean;
  error: boolean;
  canRun: boolean;
  onRun: (scenario: string) => void;
  onRetry: () => void;
};

export function LabView({ status, loading, error, canRun, onRun, onRetry }: LabViewProps) {
  if (loading) {
    return (
      <p role="status" className="lab-state">
        Cargando laboratorio
      </p>
    );
  }

  if (error) {
    return (
      <section role="alert" className="lab-state lab-state--error">
        <p>No se pudo cargar el estado del laboratorio.</p>
        <button type="button" onClick={onRetry}>
          Reintentar
        </button>
      </section>
    );
  }

  const isActive = status !== null && ACTIVE_STATUSES.has(status.status);
  const buttonsDisabled = !canRun || isActive;

  return (
    <div className="lab-page">
      <h1 className="lab-title">Laboratorio</h1>

      <div className="lab-scenarios">
        {SCENARIOS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            className="lab-scenario-button"
            disabled={buttonsDisabled}
            onClick={() => onRun(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {status !== null && (
        <div className="lab-status">
          <span className="lab-status-label">Estado:</span>
          <span className={STATUS_STYLE[status.status] ?? "lab-badge"}>
            {status.status}
          </span>
          <span className="lab-status-scenario">
            {status.scenario} — actor: {status.actor}
          </span>
        </div>
      )}

      {status?.log_text && (
        <div className="lab-terminal" aria-label="Terminal de ejecución">
          <pre className="lab-terminal-content">{status.log_text}</pre>
        </div>
      )}
    </div>
  );
}
