import { useEffect, useState } from "react";
import { Play, Square, Wifi, WifiOff, Bell, BellOff, LogOut, ShieldCheck, Globe } from "lucide-react";
import { useWebSocket } from "./hooks/useWebSocket";
import { useAwayAlerts } from "./hooks/useAwayAlerts";
import { authFetch, clearSession, getStoredUser, getToken } from "./auth";
import ParticipantCard from "./components/ParticipantCard";
import LiveStats from "./components/LiveStats";
import SessionSummary from "./components/SessionSummary";
import ParticipantLinkPanel from "./components/ParticipantLinkPanel";
import ParticipantSelfView from "./components/ParticipantSelfView";
import BrowserScreenCapture from "./components/BrowserScreenCapture";
import LivePreview from "./components/LivePreview";
import Login from "./components/Login";
import ResetPassword from "./components/ResetPassword";
import AdminPanel from "./components/AdminPanel";
import SiteSettings from "./components/SiteSettings";

function HostDashboard({ user, onLogout }) {
  const { participants, lastTimestamp, connected } = useWebSocket();
  const { permission: notifPermission, requestPermission: requestNotifPermission } = useAwayAlerts(participants);
  const [sessionActive, setSessionActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [showSiteSettings, setShowSiteSettings] = useState(false);

  async function toggleSession() {
    setLoading(true);
    try {
      const endpoint = sessionActive ? "/api/session/stop" : "/api/session/start";
      const res = await authFetch(endpoint, { method: "POST" });
      if (res.ok) setSessionActive(!sessionActive);
    } catch (err) {
      console.error("Failed to toggle session", err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-paper px-4 py-4 font-sans text-ink sm:px-6 sm:py-6">
      <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="Logo" className="h-10 w-10 flex-shrink-0 object-cover" />
          <div className="min-w-0">
            <h1 className="text-xl font-bold">SAWALA</h1>
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
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <span className="inline-flex items-center gap-1 text-xs text-neutral-500">
            {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
            {connected ? "Terhubung" : "Terputus"}
          </span>
          {notifPermission !== "unsupported" && notifPermission !== "granted" && (
            <button
              onClick={requestNotifPermission}
              className="inline-flex items-center gap-1 rounded-lg bg-paper-alt px-3 py-2 text-xs text-ink-soft transition hover:bg-line"
              title="Dapat notifikasi desktop saat ada kejadian baru walau sedang di tab lain"
            >
              <BellOff size={14} />
              <span className="hidden sm:inline">Aktifkan Notifikasi</span>
            </button>
          )}
          {notifPermission === "granted" && (
            <span className="inline-flex items-center gap-1 text-xs text-neutral-400" title="Notifikasi tab-lain aktif">
              <Bell size={14} />
            </span>
          )}
          {user?.role === "super_admin" && (
            <button
              onClick={() => setShowAdmin(true)}
              className="inline-flex items-center gap-1 rounded-lg bg-paper-alt px-3 py-2 text-xs text-ink-soft transition hover:bg-line"
            >
              <ShieldCheck size={14} />
              <span className="hidden sm:inline">Kelola User</span>
            </button>
          )}
          {user?.role === "super_admin" && (
            <button
              onClick={() => setShowSiteSettings(true)}
              className="inline-flex items-center gap-1 rounded-lg bg-paper-alt px-3 py-2 text-xs text-ink-soft transition hover:bg-line"
            >
              <Globe size={14} />
              <span className="hidden sm:inline">Site Settings</span>
            </button>
          )}
          <button
            onClick={toggleSession}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-ink-soft px-4 py-2 text-sm font-medium text-paper transition hover:bg-ink disabled:opacity-50"
          >
            {sessionActive ? <Square size={16} /> : <Play size={16} />}
            {sessionActive ? "Hentikan Sesi" : "Mulai Sesi"}
          </button>
          <button
            onClick={onLogout}
            className="inline-flex items-center gap-1 rounded-lg bg-paper-alt px-3 py-2 text-xs text-ink-soft transition hover:bg-line"
            title={user?.email}
          >
            <LogOut size={14} />
          </button>
        </div>
      </header>

      <main className="space-y-6">
        <ParticipantLinkPanel />

        <BrowserScreenCapture />

        <LivePreview />

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

      {showAdmin && <AdminPanel currentUserId={user?.id} onClose={() => setShowAdmin(false)} />}
      {showSiteSettings && <SiteSettings onClose={() => setShowSiteSettings(false)} />}
    </div>
  );
}

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const isParticipantView = params.get("view") === "saya";
  const isResetPasswordView = window.location.pathname.endsWith("/reset-password");

  const [user, setUser] = useState(getStoredUser());

  useEffect(() => {
    if (!getToken()) return;
    authFetch("/api/auth/me")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setUser(data);
      });
  }, []);

  function handleLogout() {
    clearSession();
    setUser(null);
  }

  if (isParticipantView) return <ParticipantSelfView />;
  if (isResetPasswordView) return <ResetPassword />;
  if (!user || !getToken()) return <Login onLoggedIn={setUser} />;

  return <HostDashboard user={user} onLogout={handleLogout} />;
}
