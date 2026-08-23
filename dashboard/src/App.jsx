import { useState } from "react";
import { Play, Square, Wifi, WifiOff } from "lucide-react";
import { useWebSocket } from "./hooks/useWebSocket";
import { API_BASE } from "./api";
import ParticipantCard from "./components/ParticipantCard";
import LiveStats from "./components/LiveStats";
import SessionSummary from "./components/SessionSummary";
import ParticipantLinkPanel from "./components/ParticipantLinkPanel";
import ParticipantSelfView from "./components/ParticipantSelfView";
import ScreenPreview from "./components/ScreenPreview";

function HostDashboard() {
  const { participants, lastTimestamp, connected } = useWebSocket();
  const [sessionActive, setSessionActive] = useState(false);
  const [loading, setLoading] = useState(false);

  async function toggleSession() {
    setLoading(true);
    try {
      const endpoint = sessionActive ? "/api/session/stop" : "/api/session/start";
      const res = await fetch(`${API_BASE}${endpoint}`, { method: "POST" });
      if (res.ok) setSessionActive(!sessionActive);
    } catch (err) {
      console.error("Failed to toggle session", err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-paper px-6 py-6 font-sans text-ink">
      <header className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src="/logo.png" alt="Logo" className="h-10 w-10 object-cover" />
          <div>
            <h1 className="text-xl font-bold">Meeting Monitor</h1>
            <p className="text-xs text-neutral-500">
              Host Monitoring Dashboard
            {lastTimestamp && (
              <span className="ml-2 text-neutral-400">
                Update terakhir: {new Date(lastTimestamp).toLocaleTimeString()}
              </span>
            )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1 text-xs text-neutral-500">
            {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
            {connected ? "Terhubung" : "Terputus"}
          </span>
          <button
            onClick={toggleSession}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-ink px-4 py-2 text-sm font-medium text-ink hover:bg-ink hover:text-paper disabled:opacity-50"
          >
            {sessionActive ? <Square size={16} /> : <Play size={16} />}
            {sessionActive ? "Hentikan Sesi" : "Mulai Sesi"}
          </button>
        </div>
      </header>

      <main className="space-y-6">
        <ParticipantLinkPanel />

        <ScreenPreview />

        <LiveStats participants={participants} />

        <section>
          <h2 className="mb-3 text-sm font-semibold text-neutral-700">Panel Peserta</h2>
          {participants.length === 0 ? (
            <p className="text-sm text-neutral-500">
              Belum ada data peserta. Mulai sesi untuk memulai monitoring.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {participants.map((p) => (
                <ParticipantCard key={p.id} participant={p} />
              ))}
            </div>
          )}
        </section>

        <SessionSummary participants={participants} />
      </main>
    </div>
  );
}

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const isParticipantView = params.get("view") === "saya";

  return isParticipantView ? <ParticipantSelfView /> : <HostDashboard />;
}
