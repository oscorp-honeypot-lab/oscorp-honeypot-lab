import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Clock3,
  Download,
  RefreshCw,
  Server,
  ShieldAlert,
  Users,
} from "lucide-react";
import { getSummary, getTimeline } from "../../api/client";
import { EChart } from "./EChart";
import { riskOption, timelineOption } from "./chartOptions";

const number = new Intl.NumberFormat("es-AR");

export function DashboardPage() {
  const [hours, setHours] = useState(24);
  const summary = useQuery({
    queryKey: ["analytics", "summary"],
    queryFn: getSummary,
    refetchInterval: 60_000,
  });
  const timeline = useQuery({
    queryKey: ["analytics", "timeline", hours],
    queryFn: () => getTimeline(hours),
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
