import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, LogIn, ShieldCheck } from "lucide-react";
import { useAuth } from "./AuthProvider";

export function LoginPage() {
  const { user, login, loginPending, loginError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showPassword, setShowPassword] = useState(false);

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await login({
      username: String(form.get("username") ?? ""),
      password: String(form.get("password") ?? ""),
    });
    const destination =
      (location.state as { from?: { pathname?: string } } | null)?.from
        ?.pathname ?? "/dashboard";
    navigate(destination, { replace: true });
  }

  return (
    <main className="login-page">
      <section className="login-brand" aria-label="OSCORP ThreatLab">
        <div className="brand-mark">
          <ShieldCheck aria-hidden="true" />
        </div>
        <p className="brand-kicker">OSCORP</p>
        <h1>ThreatLab</h1>
        <p className="login-subtitle">
          Consola operativa de actividad SSH maliciosa
        </p>
      </section>

      <section className="login-panel">
        <div>
          <p className="section-label">Acceso seguro</p>
          <h2>Iniciar sesión</h2>
        </div>
        <form onSubmit={submit} className="login-form">
          <label>
            Usuario
            <input
              name="username"
              autoComplete="username"
              required
              maxLength={64}
            />
          </label>
          <label>
            Contraseña
            <span className="password-field">
              <input
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                maxLength={128}
              />
              <button
                type="button"
                className="icon-button"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={
                  showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                }
                title={
                  showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                }
              >
                {showPassword ? <EyeOff /> : <Eye />}
              </button>
            </span>
          </label>
          {loginError && (
            <p className="form-error" role="alert">
              Credenciales inválidas o acceso temporalmente bloqueado.
            </p>
          )}
          <button className="primary-button" disabled={loginPending}>
            <LogIn aria-hidden="true" />
            {loginPending ? "Validando" : "Ingresar"}
          </button>
        </form>
      </section>
    </main>
  );
}
