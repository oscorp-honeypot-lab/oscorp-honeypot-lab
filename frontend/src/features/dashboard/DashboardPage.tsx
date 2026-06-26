import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Clock3,
  Download,
  FileText,
  Globe,
  RefreshCw,
  Send,
  Server,
  ShieldAlert,
  Timer,
  Users,
} from "lucide-react";
import {
  downloadLatestReport,
  getGeoStats,
  getMttdStats,
  getSummary,
  getTimeline,
  sendLatestReportTelegram,
} from "../../api/client";
import type {
  GeoCountryStatResponse,
  MttdTriggerStatResponse,
} from "../../api/generated/types.gen";
import { EChart } from "./EChart";
import { riskOption, timelineOption } from "./chartOptions";

const number = new Intl.NumberFormat("es-AR");
const LIVE_REFRESH_MS = 10_000;

export function DashboardPage() {
  const [hours, setHours] = useState(24);
  const [reportBusy, setReportBusy] = useState<string | null>(null);
  const [reportStatus, setReportStatus] = useState<string>("");
  const summary = useQuery({
    queryKey: ["analytics", "summary"],
    queryFn: getSummary,
    refetchInterval: LIVE_REFRESH_MS,
  });
  const timeline = useQuery({
    queryKey: ["analytics", "timeline", hours],
    queryFn: () => getTimeline(hours),
    refetchInterval: LIVE_REFRESH_MS,
  });
  const mttd = useQuery({
    queryKey: ["analytics", "mttd"],
    queryFn: getMttdStats,
    refetchInterval: LIVE_REFRESH_MS,
  });
  const geo = useQuery({
    queryKey: ["analytics", "geo"],
    queryFn: getGeoStats,
    refetchInterval: 60_000,
  });

  const timelineChart = useMemo(
    () => (timeline.data ? timelineOption(timeline.data) : null),
    [timeline.data],
  );
  const riskChart = useMemo(
    () => (summary.data ? riskOption(summary.data) : null),
    [summary.data],
  );

  if (summary.isLoading || timeline.isLoading) {
    return <DashboardSkeleton />;
  }
  if (summary.isError || timeline.isError || !summary.data || !timeline.data) {
    return (
      <section className="dashboard-state" role="alert">
        <ShieldAlert aria-hidden="true" />
        <h1>No se pudo cargar el dashboard</h1>
        <button
          className="secondary-button"
          onClick={() => {
            void summary.refetch();
            void timeline.refetch();
          }}
        >
          <RefreshCw aria-hidden="true" />
          Reintentar
        </button>
      </section>
    );
  }

  const latest = summary.data.latest_event_at
    ? new Intl.DateTimeFormat("es-AR", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(summary.data.latest_event_at))
    : "Sin actividad";

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <div>
          <p className="section-label">Vista general</p>
          <h1>Actividad de amenazas</h1>
        </div>
        <div className="live-status">
          <span />
          LAB operativo
        </div>
      </header>

      <section className="metric-grid" aria-label="Resumen operativo">
        <Metric
          icon={<Activity />}
          label="Eventos"
          value={number.format(summary.data.events)}
        />
        <Metric
          icon={<Server />}
          label="Sesiones"
          value={number.format(summary.data.sessions)}
        />
        <Metric
          icon={<Users />}
          label="IPs únicas"
          value={number.format(summary.data.unique_source_ips)}
        />
        <Metric
          icon={<ShieldAlert />}
          label="Login exitoso"
          value={number.format(summary.data.successful_login_sessions)}
        />
        <Metric
          icon={<Download />}
          label="Con descargas"
          value={number.format(summary.data.download_sessions)}
        />
      </section>

      <section className="dashboard-grid">
        <div className="chart-panel timeline-panel">
          <div className="panel-heading">
            <div>
              <p className="section-label">Evolución temporal</p>
              <h2>Eventos y sesiones</h2>
            </div>
            <div className="segmented-control" aria-label="Período">
              {[24, 72, 168].map((value) => (
                <button
                  key={value}
                  className={hours === value ? "active" : ""}
                  onClick={() => setHours(value)}
                >
                  {value === 168 ? "7d" : `${value}h`}
                </button>
              ))}
            </div>
          </div>
          {timelineChart && (
            <EChart
              option={timelineChart}
              label="Evolución de eventos y sesiones"
            />
          )}
        </div>

        <div className="chart-panel risk-panel">
          <div className="panel-heading">
            <div>
              <p className="section-label">Attack Risk Score</p>
              <h2>Distribución de riesgo</h2>
            </div>
          </div>
          {riskChart && (
            <EChart option={riskChart} label="Distribución de riesgo" />
          )}
        </div>
      </section>

      <section className="activity-band">
        <Clock3 aria-hidden="true" />
        <div>
          <span>Último evento registrado</span>
          <strong>{latest}</strong>
        </div>
        <div>
          <span>Sesiones de riesgo alto o crítico</span>
          <strong>
            {number.format(
              summary.data.risk_high + summary.data.risk_critical,
            )}
          </strong>
        </div>
      </section>

      {mttd.data && <MttdPanel stats={mttd.data} />}
      <ReportPanel
        busy={reportBusy}
        status={reportStatus}
        onDownload={async (periodType, format) => {
          const key = `${periodType}-${format}-download`;
          setReportBusy(key);
          setReportStatus("");
          try {
            await downloadLatestReport(periodType, format);
            setReportStatus("Descarga preparada");
          } catch {
            setReportStatus("No se pudo descargar el reporte");
          } finally {
            setReportBusy(null);
          }
        }}
        onTelegram={async (periodType) => {
          const key = `${periodType}-telegram`;
          setReportBusy(key);
          setReportStatus("");
          try {
            const delivery = await sendLatestReportTelegram(periodType, "html");
            setReportStatus(
              delivery.status === "skipped"
                ? "Telegram no configurado"
                : "Reporte enviado a Telegram",
            );
          } catch {
            setReportStatus("No se pudo enviar el reporte");
          } finally {
            setReportBusy(null);
          }
        }}
      />
      {geo.data && <GeoPanel stats={geo.data} />}
    </div>
  );
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <article className="metric">
      <span className="metric-icon">{icon}</span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </article>
  );
}

const TRIGGER_LABELS: Record<string, string> = {
  high_risk: "Alto riesgo",
  successful_login: "Login exitoso",
  file_download: "Descarga",
};

function fmt(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

function MttdPanel({
  stats,
}: {
  stats: {
    avg_seconds: number | null;
    min_seconds: number | null;
    max_seconds: number | null;
    p95_seconds: number | null;
    total_sent: number;
    total_failed: number;
    total_pending: number;
    failure_rate: number;
    by_trigger: MttdTriggerStatResponse[];
  };
}) {
  const failurePct = (stats.failure_rate * 100).toFixed(1);
  return (
    <section className="mttd-panel" aria-label="MTTD — Tiempo medio de detección">
      <div className="panel-heading">
        <div>
          <p className="section-label">Alertas Telegram</p>
          <h2>Tiempo medio de detección (MTTD)</h2>
        </div>
      </div>

      <div className="mttd-stats-grid">
        <div className="mttd-stat">
          <Timer aria-hidden="true" size={18} />
          <span>Promedio</span>
          <strong>{fmt(stats.avg_seconds)}</strong>
        </div>
        <div className="mttd-stat">
          <Timer aria-hidden="true" size={18} />
          <span>Mínimo</span>
          <strong>{fmt(stats.min_seconds)}</strong>
        </div>
        <div className="mttd-stat">
          <Timer aria-hidden="true" size={18} />
          <span>Máximo</span>
          <strong>{fmt(stats.max_seconds)}</strong>
        </div>
        <div className="mttd-stat">
          <Timer aria-hidden="true" size={18} />
          <span>Percentil 95</span>
          <strong>{fmt(stats.p95_seconds)}</strong>
        </div>
        <div className="mttd-stat">
          <Activity aria-hidden="true" size={18} />
          <span>Enviadas</span>
          <strong>{number.format(stats.total_sent)}</strong>
        </div>
        <div className="mttd-stat mttd-stat--warning">
          <AlertTriangle aria-hidden="true" size={18} />
          <span>Tasa de fallo</span>
          <strong>{failurePct}%</strong>
        </div>
      </div>

      {stats.by_trigger.length > 0 && (
        <table className="mttd-trigger-table" aria-label="MTTD por tipo de evento">
          <thead>
            <tr>
              <th>Tipo de evento</th>
              <th>Promedio</th>
              <th>Mínimo</th>
              <th>Máximo</th>
              <th>Alertas</th>
            </tr>
          </thead>
          <tbody>
            {stats.by_trigger.map((t) => (
              <tr key={t.trigger}>
                <td>{TRIGGER_LABELS[t.trigger] ?? t.trigger}</td>
                <td>{fmt(t.avg_seconds)}</td>
                <td>{fmt(t.min_seconds)}</td>
                <td>{fmt(t.max_seconds)}</td>
                <td>{number.format(t.count)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {stats.total_sent === 0 && (
        <p className="mttd-empty">
          Sin alertas enviadas aún. Configurá <code>TELEGRAM_BOT_TOKEN</code> y{" "}
          <code>TELEGRAM_CHAT_ID</code> para activar el envío.
        </p>
      )}
    </section>
  );
}

function countryFlag(code: string | null): string {
  if (!code || code.length !== 2) return "🌐";
  return [...code.toUpperCase()]
    .map((c) => String.fromCodePoint(c.charCodeAt(0) + 127397))
    .join("");
}

function ReportPanel({
  busy,
  status,
  onDownload,
  onTelegram,
}: {
  busy: string | null;
  status: string;
  onDownload: (periodType: "daily" | "weekly", format: "html" | "csv") => Promise<void>;
  onTelegram: (periodType: "daily" | "weekly") => Promise<void>;
}) {
  const periods = [
    { key: "daily" as const, label: "Diario" },
    { key: "weekly" as const, label: "Semanal" },
  ];
  return (
    <section className="report-panel" aria-label="Reportes periodicos">
      <div className="panel-heading">
        <div>
          <p className="section-label">Reportes</p>
          <h2>Entregas reproducibles</h2>
        </div>
        <FileText aria-hidden="true" size={22} />
      </div>
      <div className="report-actions">
        {periods.map((period) => (
          <div className="report-action-row" key={period.key}>
            <strong>{period.label}</strong>
            <div>
              <button
                className="icon-button"
                aria-label={`Descargar reporte ${period.label} HTML`}
                title="Descargar HTML"
                disabled={busy !== null}
                onClick={() => void onDownload(period.key, "html")}
              >
                <FileText aria-hidden="true" size={16} />
              </button>
              <button
                className="icon-button"
                aria-label={`Descargar reporte ${period.label} CSV`}
                title="Descargar CSV"
                disabled={busy !== null}
                onClick={() => void onDownload(period.key, "csv")}
              >
                <Download aria-hidden="true" size={16} />
              </button>
              <button
                className="icon-button"
                aria-label={`Enviar reporte ${period.label} por Telegram`}
                title="Enviar Telegram"
                disabled={busy !== null}
                onClick={() => void onTelegram(period.key)}
              >
                <Send aria-hidden="true" size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>
      {status && <p className="report-status">{status}</p>}
    </section>
  );
}

function GeoPanel({
  stats,
}: {
  stats: {
    total_with_geo: number;
    total_without_geo: number;
    unique_countries: number;
    by_country: GeoCountryStatResponse[];
  };
}) {
  const total = stats.total_with_geo + stats.total_without_geo;
  const coveragePct =
    total > 0 ? ((stats.total_with_geo / total) * 100).toFixed(1) : "0.0";
  return (
    <section className="geo-panel" aria-label="Origen geográfico de ataques">
      <div className="panel-heading">
        <div>
          <p className="section-label">Enriquecimiento geográfico</p>
          <h2>Origen de ataques</h2>
        </div>
        <Globe className="geo-globe-icon" aria-hidden="true" size={22} />
      </div>

      <div className="geo-stats-row">
        <div className="geo-stat">
          <span>Países únicos</span>
          <strong>{number.format(stats.unique_countries)}</strong>
        </div>
        <div className="geo-stat">
          <span>Sesiones con geo</span>
          <strong>{number.format(stats.total_with_geo)}</strong>
        </div>
        <div className="geo-stat">
          <span>Cobertura</span>
          <strong>{coveragePct}%</strong>
        </div>
        <div className="geo-stat">
          <span>Sin geo</span>
          <strong>{number.format(stats.total_without_geo)}</strong>
        </div>
      </div>

      {stats.by_country.length > 0 ? (
        <table className="geo-country-table" aria-label="Top países por sesiones">
          <thead>
            <tr>
              <th>País</th>
              <th>Sesiones</th>
              <th>IPs únicas</th>
            </tr>
          </thead>
          <tbody>
            {stats.by_country.map((c) => (
              <tr key={c.country}>
                <td>
                  <span className="geo-flag" aria-hidden="true">
                    {countryFlag(c.country_code ?? null)}
                  </span>
                  {c.country}
                </td>
                <td>{number.format(c.session_count)}</td>
                <td>{number.format(c.unique_ips)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="geo-empty">
          Sin datos geográficos disponibles. Las IPs privadas (LAB) no se
          enriquecen con datos de ubicación. Con IPs públicas reales se
          mostrará el origen de los ataques.
        </p>
      )}
    </section>
  );
}

function DashboardSkeleton() {
  return (
    <div className="dashboard-page" aria-label="Cargando dashboard">
      <div className="skeleton header-skeleton" />
      <div className="metric-grid">
        {Array.from({ length: 5 }, (_, index) => (
          <div className="skeleton metric-skeleton" key={index} />
        ))}
      </div>
      <div className="dashboard-grid">
        <div className="skeleton chart-skeleton" />
        <div className="skeleton chart-skeleton" />
      </div>
    </div>
  );
}
