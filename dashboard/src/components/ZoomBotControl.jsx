import { useEffect, useRef, useState } from "react";
import { Bot, Play, Square } from "lucide-react";
import { authFetch } from "../auth";

const STATUS_POLL_MS = 3000;

export default function ZoomBotControl() {
  const [joinUrl, setJoinUrl] = useState("");
  const [passcode, setPasscode] = useState("");
  const [status, setStatus] = useState({ running: false, log_tail: [] });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const logRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await authFetch("/api/bot/status");
        if (!cancelled && res.ok) setStatus(await res.json());
      } catch {
        // diam - retry di tick berikutnya
      }
    }

    poll();
    const timer = setInterval(poll, STATUS_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [status.log_tail]);

  async function start() {
    if (!joinUrl.trim()) {
      setError("Link join Zoom belum diisi.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const res = await authFetch("/api/bot/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          join_url: joinUrl.trim(),
          display_name: "SAWALA",
          passcode: passcode.trim() || null,
        }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        setError(data?.detail || `Gagal menjalankan bot (${res.status})`);
      }
    } catch {
      setError("Tidak bisa menghubungi server.");
    } finally {
      setBusy(false);
    }
  }

  async function stop() {
    setBusy(true);
    try {
      await authFetch("/api/bot/stop", { method: "POST" });
    } catch {
      setError("Tidak bisa menghubungi server.");
    } finally {
      setBusy(false);
    }
  }

  async function clearLog() {
    setBusy(true);
    try {
      const res = await authFetch("/api/bot/clear-log", { method: "POST" });
      if (res.ok) setStatus((s) => ({ ...s, log_tail: [] }));
    } catch {
      setError("Tidak bisa menghubungi server.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-line bg-card p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-ink-soft">
        <Bot size={16} />
        Bot SAWALA - Join Zoom Otomatis
      </div>
      <p className="mt-1 text-xs text-neutral-500">
        Bot join meeting sendiri sebagai peserta bernama "SAWALA", baca nama asli peserta langsung dari
        Zoom (bukan tebakan), lalu kirim video tiap peserta ke sistem ini. Lebih akurat daripada Screen
        Capture di atas - tidak perlu kamu buka/share apa pun. Mulai sesi monitoring dulu sebelum start bot.
      </p>

      {!status.running && (
        <div className="mt-3 space-y-2">
          <input
            type="text"
            value={joinUrl}
            onChange={(e) => setJoinUrl(e.target.value)}
            placeholder="Link 'Join from Browser' Zoom, mis. https://xxxx.zoom.us/wc/join/1234567890"
            className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm"
          />
          <input
            type="text"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
            placeholder="Passcode meeting (kosongkan kalau tidak ada)"
            className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm"
          />
        </div>
      )}

      <div className="mt-3 flex items-center gap-2">
        {status.running ? (
          <button
            onClick={stop}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg bg-ink-soft px-4 py-2 text-sm font-medium text-paper transition hover:bg-ink disabled:opacity-50"
          >
            <Square size={16} />
            Hentikan Bot
          </button>
        ) : (
          <button
            onClick={start}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg bg-ink-soft px-4 py-2 text-sm font-medium text-paper transition hover:bg-ink disabled:opacity-50"
          >
            <Play size={16} />
            Mulai Bot
          </button>
        )}
        <span className="text-xs text-neutral-500">
          {status.running ? "Bot sedang berjalan" : "Bot tidak aktif"}
        </span>
        {!status.running && status.log_tail?.length > 0 && (
          <button
            onClick={clearLog}
            disabled={busy}
            className="ml-auto text-xs text-neutral-500 underline hover:text-neutral-700 disabled:opacity-50"
          >
            Bersihkan log
          </button>
        )}
      </div>

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}

      {status.log_tail?.length > 0 && (
        <pre
          ref={logRef}
          className="mt-3 max-h-40 overflow-y-auto rounded-lg border border-line bg-paper-alt p-2 text-[11px] leading-relaxed text-neutral-600"
        >
          {status.log_tail.join("\n")}
        </pre>
      )}
    </div>
  );
}
