// Tiny fetch wrapper. One place to change if the API base URL ever moves.
//
// In dev, Vite proxies /api -> http://localhost:8000 (see vite.config.js),
// so we can just use relative URLs everywhere.

const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export const api = {
  getRandomFortune: () => request("/fortunes/random"),
  listFortunes: () => request("/fortunes?limit=50"),
  toggleFavorite: (id) => request(`/fortunes/${id}/favorite`, { method: "PATCH" }),
};
