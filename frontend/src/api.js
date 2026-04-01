const API_BASE = import.meta.env.VITE_API_BASE || "/api";
const BASIC_AUTH = import.meta.env.VITE_BASIC_AUTH || "";

const basicAuthHeader = BASIC_AUTH
  ? `Basic ${btoa(BASIC_AUTH)}`
  : null;

export async function login(username, password) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(basicAuthHeader ? { Authorization: basicAuthHeader } : {})
    },
    body: JSON.stringify({ username, password })
  });

  if (!response.ok) {
    throw new Error("Credenciales invalidas");
  }

  return response.json();
}

export async function me(token) {
  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: {
      ...(basicAuthHeader ? { Authorization: basicAuthHeader } : {}),
      "X-Access-Token": `Bearer ${token}`
    }
  });

  if (!response.ok) {
    throw new Error("Sesion invalida");
  }

  return response.json();
}
