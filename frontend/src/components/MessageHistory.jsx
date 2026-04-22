import { useEffect, useState } from "react";
import { api } from "../api.js";

/**
 * MessageHistory
 * --------------
 * Shows the list of previously drawn fortunes, newest first.
 * Re-fetches whenever `refreshKey` changes (parent bumps it after a new draw).
 */
export default function MessageHistory({ refreshKey }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setItems(await api.listFortunes());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [refreshKey]);

  async function onFavorite(id) {
    const updated = await api.toggleFavorite(id);
    setItems((prev) => prev.map((it) => (it.id === id ? updated : it)));
  }

  return (
    <section className="w-full max-w-2xl mx-auto mt-10 px-4">
      <h2 className="text-xl font-semibold text-stone-700 mb-3">Your fortunes</h2>
      {loading && <p className="text-stone-500">Loading…</p>}
      {error && <p className="text-red-600 text-sm">Error: {error}</p>}
      {!loading && items.length === 0 && (
        <p className="text-stone-500 text-sm">
          No fortunes yet. Click the cookie above to draw your first one.
        </p>
      )}
      <ul className="space-y-2">
        {items.map((item) => (
          <li
            key={item.id}
            className="bg-white rounded-lg shadow-sm border border-stone-200 px-4 py-3 flex items-start gap-3"
          >
            <button
              onClick={() => onFavorite(item.id)}
              className="text-2xl leading-none"
              aria-label={item.is_favorite ? "Unfavorite" : "Favorite"}
              title={item.is_favorite ? "Unfavorite" : "Favorite"}
            >
              {item.is_favorite ? "♥" : "♡"}
            </button>
            <div className="flex-1">
              <p className="text-stone-800">{item.message}</p>
              <p className="text-xs text-stone-400 mt-1">
                {new Date(item.created_at).toLocaleString()}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
