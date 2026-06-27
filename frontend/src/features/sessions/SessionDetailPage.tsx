import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  RefreshCw,
  Search,
  ShieldAlert,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import {
  ApiError,
  getSessionDetail,
  reviewSession,
} from "../../api/client";
import type {
  SessionDetailResponse,
  SessionListItemResponse,
} from "../../api/generated/types.gen";
import { useAuth } from "../auth/AuthProvider";

const dateTime = new Intl.DateTimeFormat("es-AR", {
  dateStyle: "short",
  timeStyle: "short",
});
const LIVE_REFRESH_MS = 10_000;

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return dateTime.format(new Date(value));
}

function riskLabel(value: string | null) {
  return (
    {
      low: "Bajo",
      medium: "Medio",
      high: "Alto",
      critical: "Crítico",
    }[value ?? ""] ?? "Sin score"
  );
}

function reasonEvidence(value: unknown): string {
  return Array.isArray(value) ? value.map(String).join(", ") : "";
}

// --- Presentational ---

export type SessionDetailViewProps = {
  loading: boolean;
  notFound: boolean;
  error: boolean;
  data: SessionDetailResponse | undefined;
  reviewing: boolean;
  canReview: boolean;
  onReview: (reviewed: boolean) => void;
  onRetry: () => void;
};

export function SessionDetailView({
  loading,
  notFound,
  error,
  data,
  reviewing,
  canReview,
  onReview,
  onRetry,
}: SessionDetailViewProps) {
  if (loading) {
    return (
      <div className="table-state" role="status">
        <div className="route-loader" aria-hidden="true" />
        <span>Cargando sesión</span>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="table-state" role="status">
        <Search aria-hidden="true" />
        <strong>Sesión no encontrada</strong>
        <span>La sesión que buscás no existe o fue eliminada.</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="table-state error-state" role="alert">
        <ShieldAlert aria-hidden="true" />
        <strong>No se pudo cargar la sesión</strong>
        <button className="secondary-button" type="button" onClick={onRetry}>
          <RefreshCw aria-hidden="true" />
          Reintentar
        </button>
      </div>
    );
  }

  if (!data) return null;

  const { session, score, commands, downloads, events } = data;

  return (
    <div className="detail-page">
      <header className="detail-header">
        <div className="detail-header-main">
          <p className="section-label">Análisis de sesión</p>
          <h1 className="detail-ip">{session.src_ip ?? "IP desconocida"}</h1>
          <div className="detail-meta">
            <div className="detail-meta-item">
              <span>ID de sesión</span>
              <code>{session.session_id}</code>
            </div>
            <div className="detail-meta-item">
              <span>Primer evento</span>
              <strong>{formatDate(session.first_event_at)}</strong>
            </div>
            <div className="detail-meta-item">
              <span>Último evento</span>
              <strong>{formatDate(session.last_event_at)}</strong>
            </div>
            {session.duration_seconds != null && (
              <div className="detail-meta-item">
                <span>Duración</span>
                <strong>{session.duration_seconds.toFixed(0)} s</strong>
              </div>
            )}
            <div className="detail-meta-item">
              <span>Usuario</span>
              <strong>{session.username ?? "Desconocido"}</strong>
            </div>
            {session.country && (
              <div className="detail-meta-item">
                <span>País</span>
                <strong>{session.country}</strong>
              </div>
            )}
          </div>
        </div>

        <div className="detail-header-side">
          <span
            className={`source-mode-badge source-mode-${session.source_mode}`}
          >
            {session.source_mode === "real" ? "REAL" : "LAB"}
          </span>
          <span className={`risk-badge risk-${session.risk_level ?? "none"}`}>
            {riskLabel(session.risk_level)}
            {session.risk_score != null && ` · ${session.risk_score}`}
          </span>
          {session.reviewed && session.reviewed_by_username && (
            <p className="reviewed-by">
              Revisada por <strong>{session.reviewed_by_username}</strong>
              {session.reviewed_at && ` · ${formatDate(session.reviewed_at)}`}
            </p>
          )}
          {canReview && (
            <button
              type="button"
              className={session.reviewed ? "secondary-button" : "primary-button"}
              disabled={reviewing}
              onClick={() => onReview(!session.reviewed)}
            >
              {session.reviewed ? "Quitar revisión" : "Marcar como revisada"}
            </button>
          )}
        </div>
      </header>

      {score && (
        <section className="detail-section" aria-labelledby="score-heading">
          <h2 id="score-heading">Attack Risk Score</h2>
          <div className="score-body">
            <div className="score-dial">
              <span className={`score-number risk-${score.level}`}>
                {score.score}
              </span>
              <span className={`risk-badge risk-${score.level}`}>
                {riskLabel(score.level)}
              </span>
              <span className="score-version">v{score.rules_version}</span>
            </div>
            {score.reasons.length > 0 && (
              <ul className="score-reasons" aria-label="Reglas activadas">
                {score.reasons.map((reason, index) => (
                  <li key={index} className="reason-item">
                    <code className="reason-id">
                      {String(reason["rule_id"] ?? `regla-${index}`)}
                    </code>
                    <span className="reason-weight">
                      +{String(reason["weight"] ?? 0)} pts
                    </span>
                    {reasonEvidence(reason["evidence"]) && (
                      <span className="reason-evidence">
                        {reasonEvidence(reason["evidence"])}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      )}

      {commands.length > 0 && (
        <section className="detail-section" aria-labelledby="commands-heading">
          <h2 id="commands-heading">
            Comandos ejecutados
            <span className="detail-count">{commands.length}</span>
          </h2>
          <ol className="command-log" aria-label="Lista de comandos">
            {commands.map((cmd, index) => (
              <li key={index}>
                <code>{cmd}</code>
              </li>
            ))}
          </ol>
        </section>
      )}

      {downloads.length > 0 && (
        <section className="detail-section" aria-labelledby="downloads-heading">
          <h2 id="downloads-heading">
            Descargas
            <span className="detail-count">{downloads.length}</span>
          </h2>
          <div className="detail-table-wrap">
            <table className="detail-table">
              <caption className="visually-hidden">
                Archivos descargados durante la sesión
              </caption>
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">URL</th>
                  <th scope="col">SHA-256</th>
                </tr>
              </thead>
              <tbody>
                {downloads.map((dl, index) => (
                  <tr key={index}>
                    <td>{formatDate(dl.timestamp)}</td>
                    <td>
                      <code className="url-cell">{dl.url ?? "—"}</code>
                    </td>
                    <td>
                      <code className="hash-cell">{dl.sha256 ?? "—"}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="detail-section" aria-labelledby="events-heading">
        <h2 id="events-heading">
          Eventos
          <span className="detail-count">{events.length}</span>
        </h2>
        <div className="detail-table-wrap">
          <table className="detail-table">
            <caption className="visually-hidden">
              Línea temporal de eventos de la sesión
            </caption>
            <thead>
              <tr>
                <th scope="col">Timestamp</th>
                <th scope="col">Tipo</th>
                <th scope="col">Usuario</th>
                <th scope="col">Detalle</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id}>
                  <td>{formatDate(event.timestamp)}</td>
                  <td>
                    <code className="event-type">{event.event_type ?? "—"}</code>
                  </td>
                  <td>{event.username ?? "—"}</td>
                  <td>
                    <code className="url-cell">
                      {event.command ?? event.url ?? "—"}
                    </code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

// --- Container ---

export function SessionDetailPage() {
  const { sessionKey } = useParams<{ sessionKey: string }>();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const detailQuery = useQuery({
    queryKey: ["sessions", "detail", sessionKey],
    queryFn: () => getSessionDetail(sessionKey!),
    retry: (count, error) =>
      error instanceof ApiError && error.status === 404 ? false : count < 1,
    enabled: !!sessionKey,
    refetchInterval: LIVE_REFRESH_MS,
  });

  const reviewMutation = useMutation({
    mutationFn: (reviewed: boolean) => reviewSession(sessionKey!, reviewed),
    onSuccess: (updated: SessionListItemResponse) => {
      queryClient.setQueryData(
        ["sessions", "detail", sessionKey],
        (old: SessionDetailResponse | undefined) =>
          old ? { ...old, session: updated } : old,
      );
    },
  });

  const isNotFound =
    detailQuery.isError &&
    detailQuery.error instanceof ApiError &&
    detailQuery.error.status === 404;

  const isError = detailQuery.isError && !isNotFound;
  const canReview = user?.role === "analyst" || user?.role === "admin";

  return (
    <div>
      <nav className="detail-nav" aria-label="Navegación de detalle">
        <Link to="/sessions" className="detail-back">
          ← Volver a sesiones
        </Link>
      </nav>
      <SessionDetailView
        loading={detailQuery.isLoading}
        notFound={isNotFound}
        error={isError}
        data={detailQuery.data}
        reviewing={reviewMutation.isPending}
        canReview={canReview}
        onReview={reviewMutation.mutate}
        onRetry={() => void detailQuery.refetch()}
      />
    </div>
  );
}
