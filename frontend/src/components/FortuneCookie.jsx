import { useState } from "react";
import { api } from "../api.js";
import SourceBadge from "./SourceBadge.jsx";

/**
 * FortuneCookie
 * -------------
 * Renders a cookie the user can click. On click:
 *  1. The cookie "shakes" briefly.
 *  2. We call the API to get a random fortune.
 *  3. The two halves slide apart (crack animation).
 *  4. A paper slip pops up with the message.
 *
 * State machine:
 *   idle  -> shaking -> cracked (paper shown) -> idle (after reset)
 */
export default function FortuneCookie({ onNewFortune }) {
  const [stage, setStage] = useState("idle");
  const [fortune, setFortune] = useState(null);
  const [error, setError] = useState(null);

  async function crack() {
    if (stage !== "idle") return;
    setError(null);
    setStage("shaking");
    try {
      // Small delay so the shake animation is visible before cracking.
      await new Promise((r) => setTimeout(r, 450));
      const data = await api.getRandomFortune();
      setFortune(data);
      setStage("cracked");
      onNewFortune?.(data);
    } catch (e) {
      setError(e.message);
      setStage("idle");
    }
  }

  function reset() {
    setStage("idle");
    setFortune(null);
  }

  return (
    <div className="flex flex-col items-center gap-6 py-8">
      <div
        className="relative h-48 w-96 flex items-center justify-center cursor-pointer select-none"
        onClick={crack}
        role="button"
        aria-label="Crack the fortune cookie"
      >
        <div
          className={`cookie-half left absolute ${
            stage === "shaking" ? "animate-shake" : ""
          } ${stage === "cracked" ? "animate-crack-left" : ""}`}
          style={{ left: "calc(50% - 10rem)" }}
        />
        <div
          className={`cookie-half right absolute ${
            stage === "shaking" ? "animate-shake" : ""
          } ${stage === "cracked" ? "animate-crack-right" : ""}`}
          style={{ left: "50%" }}
        />

        {stage === "cracked" && fortune && (
          <div className="absolute z-10 animate-paper-pop">
            <div className="bg-white shadow-lg px-6 py-4 rounded-sm border border-amber-200 max-w-xs text-center">
              <div className="flex justify-center mb-2">
                <SourceBadge source={fortune.source} />
              </div>
              <p className="text-stone-800 italic text-lg leading-snug">
                "{fortune.message}"
              </p>
              <p className="text-xs text-stone-400 mt-2">
                #{fortune.id} · {new Date(fortune.created_at).toLocaleString()}
              </p>
            </div>
          </div>
        )}
      </div>

      {stage === "idle" && (
        <p className="text-stone-500 text-sm">Click the cookie to reveal your fortune.</p>
      )}
      {stage === "cracked" && (
        <button
          onClick={reset}
          className="px-4 py-2 bg-amber-600 text-white rounded-full hover:bg-amber-700 transition"
        >
          Crack another
        </button>
      )}
      {error && <p className="text-red-600 text-sm">Error: {error}</p>}
    </div>
  );
}
