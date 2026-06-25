import { FormEvent, useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  ColumnDef,
  SortingState,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  FilterX,
  RefreshCw,
  Search,
  ShieldAlert,
} from "lucide-react";
import {
  SessionQuery,
  SessionSortField,
  getSessions,
} from "../../api/client";
import type { SessionListItemResponse } from "../../api/generated/types.gen";

type Filters = {
  srcIp: string;
  country: string;
  username: string;
  riskLevel: string;
  reviewed: string;
};

const emptyFilters: Filters = {
  srcIp: "",
  country: "",
  username: "",
  riskLevel: "",
  reviewed: "",
};

const dateTime = new Intl.DateTimeFormat("es-AR", {
  dateStyle: "short",
  timeStyle: "short",
});
const number = new Intl.NumberFormat("es-AR");

function formatDate(value: string) {
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

const columns: ColumnDef<SessionListItemResponse>[] = [
  {
    accessorKey: "last_event_at",
    header: "Última actividad",
    cell: ({ row }) => (
      <div className="table-primary">
        <strong>{formatDate(row.original.last_event_at)}</strong>
        <span title={row.original.session_id}>{row.original.session_id}</span>
      </div>
    ),
  },
  {
    accessorKey: "src_ip",
    header: "Origen",
    cell: ({ row }) => (
      <div className="table-primary">
        <strong>{row.original.src_ip ?? "Desconocida"}</strong>
        <span>{row.original.country ?? "País sin identificar"}</span>
      </div>
    ),
  },
  {
    accessorKey: "username",
    header: "Usuario",
    enableSorting: false,
    cell: ({ getValue }) => String(getValue() ?? "No informado"),
  },
  {
    accessorKey: "event_count",
    header: "Eventos",
    cell: ({ getValue }) => number.format(Number(getValue())),
  },
  {
    accessorKey: "command_count",
    header: "Comandos",
    cell: ({ getValue }) => number.format(Number(getValue())),
  },
  {
    accessorKey: "download_count",
    header: "Descargas",
    cell: ({ getValue }) => number.format(Number(getValue())),
  },
  {
    accessorKey: "risk_score",
    header: "Riesgo",
    cell: ({ row }) => (
      <span className={`risk-badge risk-${row.original.risk_level ?? "none"}`}>
        {riskLabel(row.original.risk_level)}
        {row.original.risk_score !== null && ` · ${row.original.risk_score}`}
      </span>
    ),
  },
  {
    accessorKey: "reviewed",
    header: "Revisión",
    enableSorting: false,
    cell: ({ getValue }) => (
      <span className={getValue() ? "reviewed-status" : "pending-status"}>
        {getValue() ? "Revisada" : "Pendiente"}
      </span>
    ),
  },
];

export function SessionsPage() {
  const [draftFilters, setDraftFilters] = useState(emptyFilters);
  const [filters, setFilters] = useState(emptyFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [sorting, setSorting] = useState<SortingState>([
    { id: "last_event_at", desc: true },
  ]);

  const activeSort = sorting[0] ?? { id: "last_event_at", desc: true };
  const query: SessionQuery = {
    page,
    pageSize,
    srcIp: filters.srcIp,
    country: filters.country,
    username: filters.username,
    riskLevel: filters.riskLevel,
    reviewed:
      filters.reviewed === "" ? undefined : filters.reviewed === "true",
    sortBy: activeSort.id as SessionSortField,
    sortOrder: activeSort.desc ? "desc" : "asc",
  };
  const sessions = useQuery({
    queryKey: ["sessions", query],
    queryFn: () => getSessions(query),
    placeholderData: keepPreviousData,
  });
  const data = useMemo(() => sessions.data?.items ?? [], [sessions.data]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => row.session_key,
    manualSorting: true,
    state: { sorting },
    onSortingChange: (updater) => {
      const next = typeof updater === "function" ? updater(sorting) : updater;
      setSorting(next.slice(0, 1));
      setPage(1);
    },
  });

  function applyFilters(event: FormEvent) {
    event.preventDefault();
    setFilters(draftFilters);
    setPage(1);
  }

  function clearFilters() {
    setDraftFilters(emptyFilters);
    setFilters(emptyFilters);
    setPage(1);
  }

  return (
    <div className="sessions-page">
      <header className="page-header">
        <div>
          <p className="section-label">Operaciones</p>
          <h1>Sesiones detectadas</h1>
        </div>
        <div className="results-status" aria-live="polite">
          {sessions.data
            ? `${number.format(sessions.data.pagination.total)} resultados`
            : "Consultando sesiones"}
        </div>
      </header>

      <form className="session-filters" onSubmit={applyFilters}>
        <label>
          IP de origen
          <input
            value={draftFilters.srcIp}
            onChange={(event) =>
              setDraftFilters({ ...draftFilters, srcIp: event.target.value })
            }
            placeholder="203.0.113.10"
          />
        </label>
        <label>
          País
          <input
            value={draftFilters.country}
            onChange={(event) =>
              setDraftFilters({ ...draftFilters, country: event.target.value })
            }
            placeholder="Argentina"
          />
        </label>
        <label>
          Usuario
          <input
            value={draftFilters.username}
            onChange={(event) =>
              setDraftFilters({ ...draftFilters, username: event.target.value })
            }
            placeholder="root"
          />
        </label>
        <label>
          Riesgo
          <select
            value={draftFilters.riskLevel}
            onChange={(event) =>
              setDraftFilters({
                ...draftFilters,
                riskLevel: event.target.value,
              })
            }
          >
            <option value="">Todos</option>
            <option value="low">Bajo</option>
            <option value="medium">Medio</option>
            <option value="high">Alto</option>
            <option value="critical">Crítico</option>
          </select>
        </label>
        <label>
          Revisión
          <select
            value={draftFilters.reviewed}
            onChange={(event) =>
              setDraftFilters({ ...draftFilters, reviewed: event.target.value })
            }
          >
            <option value="">Todas</option>
            <option value="false">Pendientes</option>
            <option value="true">Revisadas</option>
          </select>
        </label>
        <div className="filter-actions">
          <button className="primary-button" type="submit">
            <Search aria-hidden="true" />
            Aplicar
          </button>
          <button
            className="icon-button bordered"
            type="button"
            onClick={clearFilters}
            aria-label="Limpiar filtros"
            title="Limpiar filtros"
          >
            <FilterX aria-hidden="true" />
          </button>
        </div>
      </form>

      <SessionsTable
        table={table}
        loading={sessions.isLoading}
        error={sessions.isError}
        empty={!sessions.isLoading && !sessions.isError && data.length === 0}
        refreshing={sessions.isFetching && !sessions.isLoading}
        onRetry={() => void sessions.refetch()}
      />

      {sessions.data && sessions.data.pagination.total > 0 && (
        <nav className="table-pagination" aria-label="Paginación de sesiones">
          <label>
            Filas
            <select
              value={pageSize}
              onChange={(event) => {
                setPageSize(Number(event.target.value));
                setPage(1);
              }}
            >
              {[25, 50, 100].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <span>
            Página {sessions.data.pagination.page} de{" "}
            {sessions.data.pagination.pages}
          </span>
          <div>
            <button
              className="icon-button bordered"
              type="button"
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              disabled={page <= 1}
              aria-label="Página anterior"
              title="Página anterior"
            >
              <ChevronLeft aria-hidden="true" />
            </button>
            <button
              className="icon-button bordered"
              type="button"
              onClick={() => setPage((value) => value + 1)}
              disabled={page >= sessions.data.pagination.pages}
              aria-label="Página siguiente"
              title="Página siguiente"
            >
              <ChevronRight aria-hidden="true" />
            </button>
          </div>
        </nav>
      )}
    </div>
  );
}

type SessionsTableProps = {
  table: ReturnType<typeof useReactTable<SessionListItemResponse>>;
  loading: boolean;
  error: boolean;
  empty: boolean;
  refreshing: boolean;
  onRetry: () => void;
};

export function SessionsTable({
  table,
  loading,
  error,
  empty,
  refreshing,
  onRetry,
}: SessionsTableProps) {
  if (loading) {
    return (
      <div className="table-state" role="status">
        <div className="route-loader" aria-hidden="true" />
        <span>Cargando sesiones</span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="table-state error-state" role="alert">
        <ShieldAlert aria-hidden="true" />
        <strong>No se pudieron cargar las sesiones</strong>
        <button className="secondary-button" type="button" onClick={onRetry}>
          <RefreshCw aria-hidden="true" />
          Reintentar
        </button>
      </div>
    );
  }
  if (empty) {
    return (
      <div className="table-state" role="status">
        <Search aria-hidden="true" />
        <strong>No hay sesiones para estos filtros</strong>
        <span>Modifica los criterios para ampliar la búsqueda.</span>
      </div>
    );
  }

  return (
    <div className="table-frame" aria-busy={refreshing}>
      {refreshing && <div className="table-progress" aria-hidden="true" />}
      <div className="table-scroll">
        <table>
          <caption className="visually-hidden">
            Sesiones SSH detectadas por el honeypot
          </caption>
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const sorted = header.column.getIsSorted();
                  return (
                    <th
                      key={header.id}
                      aria-sort={
                        sorted === "asc"
                          ? "ascending"
                          : sorted === "desc"
                            ? "descending"
                            : undefined
                      }
                    >
                      {header.column.getCanSort() ? (
                        <button
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                          {sorted === "asc" ? (
                            <ArrowUp aria-hidden="true" />
                          ) : sorted === "desc" ? (
                            <ArrowDown aria-hidden="true" />
                          ) : (
                            <ArrowUpDown aria-hidden="true" />
                          )}
                        </button>
                      ) : (
                        flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
