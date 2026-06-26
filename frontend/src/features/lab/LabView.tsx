import { Bug, Eye, Lock, Terminal, Zap } from "lucide-react";
import type { LabRunResponse } from "../../api/client";

type ScenarioDef = {
  key: string;
  label: string;
  description: string;
  Icon: React.ComponentType<{ "aria-hidden": true }>;
};

const SCENARIOS: ScenarioDef[] = [
  {
    key: "brute-force",
    label: "Fuerza bruta",
    description:
      "Simula 50 intentos de login SSH con credenciales del diccionario. Genera cowrie.login.failed y cowrie.login.success.",
    Icon: Lock,
  },
  {
    key: "recon",
    label: "Reconocimiento",
    description:
      "Post-login: ejecuta whoami, id, uname, ps, netstat y más comandos de reconocimiento. Genera cowrie.command.input en cadena.",
    Icon: Eye,
  },
  {
    key: "malware-download",
    label: "Descarga malware",
    description:
      "Descarga payloads inocuos desde el servidor interno. Genera cowrie.session.file_download con SHA-256 del archivo.",
    Icon: Bug,
  },
  {
    key: "full",
    label: "Ataque completo",
    description:
      "Ejecuta brute-force + recon + descarga en secuencia. Cobertura total del pipeline, risk score y alertas Telegram.",
    Icon: Zap,
  },
];

const ACTIVE_STATUSES = new Set(["queued", "running", "processing"]);

const STATUS_CLASS: Record<string, string> = {
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
        <button type="button" className="secondary-button" onClick={onRetry}>
          Reintentar
        </button>
      </section>
    );
  }

  const isActive = status !== null && ACTIVE_STATUSES.has(status.status);
  const buttonsDisabled = !canRun || isActive;

  return (
    <div className="lab-page">
      <div className="page-header">
        <h1>Laboratorio</h1>
        {isActive && (
          <div className="live-status">
            <span />
            Ejecución activa
          </div>
        )}
      </div>

      <div className="lab-scenario-grid">
        {SCENARIOS.map(({ key, label, description, Icon }) => (
          <button
            key={key}
            type="button"
            className="lab-scenario-card"
            disabled={buttonsDisabled}
            onClick={() => onRun(key)}
          >
            <div className="lab-scenario-header">
              <div className="lab-scenario-icon">
                <Icon aria-hidden={true} />
              </div>
              <strong className="lab-scenario-name">{label}</strong>
            </div>
            <p className="lab-scenario-desc">{description}</p>
          </button>
        ))}
      </div>

      {status !== null && (
        <div className="lab-status-band">
          <Terminal aria-hidden={true} />
          <div>
            <strong>{status.scenario}</strong>
            <span>actor: {status.actor}</span>
          </div>
          <span className={STATUS_CLASS[status.status] ?? "lab-badge"}>
            {status.status}
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
