import { useEffect, useState } from "react";
import { login, me } from "./api.js";

const STORAGE_KEY = "vps_poo_token";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem(STORAGE_KEY));
  const [user, setUser] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      return;
    }

    me(token)
      .then((data) => setUser(data))
      .catch(() => {
        localStorage.removeItem(STORAGE_KEY);
        setToken(null);
      });
  }, [token]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await login(username, password);
      localStorage.setItem(STORAGE_KEY, result.access_token);
      setToken(result.access_token);
      setUser(result.user);
    } catch (err) {
      setError(err.message || "No se pudo iniciar sesion");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
    setUsername("");
    setPassword("");
  };

  if (token && user) {
    return (
      <main className="page">
        <div className="layout">
          <header className="topbar">
            <span className="brand">VPS-POO</span>
            <button className="logout" onClick={handleLogout}>
              Cerrar sesion
            </button>
          </header>
          <section className="hero card">
            <h1>Bienvenido, {user.nombre || "Carlos"}</h1>
            <p>Acceso correcto. Esta es la portada del sistema.</p>
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="page">
      <form className="card" onSubmit={handleSubmit}>
        <h1>Ingreso</h1>
        <label>
          Usuario
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label>
          Clave
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button className="primary" type="submit" disabled={loading}>
          {loading ? "Ingresando..." : "Entrar"}
        </button>
      </form>
    </main>
  );
}
