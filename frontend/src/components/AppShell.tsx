import {
  Activity,
  Gauge,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../features/auth/AuthProvider";

export function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <ShieldCheck aria-hidden="true" />
          <div>
            <strong>OSCORP</strong>
            <span>ThreatLab</span>
          </div>
        </div>
        <nav aria-label="Navegación principal">
          <NavLink to="/dashboard">
            <Gauge aria-hidden="true" />
            Dashboard
          </NavLink>
          <span className="nav-static">
            <Activity aria-hidden="true" />
            Operaciones
          </span>
        </nav>
        <div className="sidebar-user">
          <div>
            <strong>{user?.username}</strong>
            <span>{user?.role}</span>
          </div>
          <button
            type="button"
            className="icon-button inverse"
            onClick={() => void logout()}
            aria-label="Cerrar sesión"
            title="Cerrar sesión"
          >
            <LogOut />
          </button>
        </div>
      </aside>
      <main className="workspace">
        <Outlet />
      </main>
    </div>
  );
}
