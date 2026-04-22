import { useState } from "react";
import FortuneCookie from "./components/FortuneCookie.jsx";
import MessageHistory from "./components/MessageHistory.jsx";

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);

  function handleNewFortune() {
    setRefreshKey((k) => k + 1);
  }

  return (
    <main className="min-h-screen py-10">
      <header className="text-center mb-6">
        <h1 className="text-4xl font-bold text-amber-700 tracking-tight">
          Fortune Cookie
        </h1>
        <p className="text-stone-500 mt-1">Click to reveal a message.</p>
      </header>

      <FortuneCookie onNewFortune={handleNewFortune} />
      <MessageHistory refreshKey={refreshKey} />

      <footer className="text-center text-stone-400 text-xs mt-16">
        Built as a DevOps/SRE portfolio project · FastAPI + React + Tailwind
      </footer>
    </main>
  );
}
