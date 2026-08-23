import { useEffect, useRef, useState } from "react";
import { Monitor, RefreshCw } from "lucide-react";
import { API_BASE } from "../api";

const REFRESH_MS = 3000;

export default function ScreenPreview() {
  const [src, setSrc] = useState(null);
  const [error, setError] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      try {
        const res = await fetch(`${API_BASE}/api/preview?t=${Date.now()}`);
        if (!res.ok) throw new Error("preview not available");
        const blob = await res.blob();
        if (cancelled) return;
        setSrc((prev) => {
          if (prev) URL.revokeObjectURL(prev);
          return URL.createObjectURL(blob);
        });
        setError(false);
      } catch {
        if (!cancelled) setError(true);
      }
    }

    refresh();
    timerRef.current = setInterval(refresh, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timerRef.current);
    };
  }, []);

  return (
    <div className="rounded-xl border border-neutral-300 bg-white p-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-ink">
          <Monitor size={16} />
          Preview Layar yang Di-capture
        </div>
        <span className="inline-flex items-center gap-1 text-xs text-neutral-400">
          <RefreshCw size={12} />
          Update tiap {REFRESH_MS / 1000}s
        </span>
      </div>
      <p className="mb-3 text-xs text-neutral-500">
        Kotak hijau = sudah terkonfirmasi jadi peserta. Kotak abu-abu = ada wajah terdeteksi tapi belum
        terkonfirmasi, atau tile tanpa wajah.
      </p>

      {error && !src && (
        <p className="text-sm text-neutral-400">
          Preview belum tersedia. Pastikan backend jalan dan sudah pernah melakukan capture.
        </p>
      )}

      {src && (
        <img
          src={src}
          alt="Preview layar yang di-capture"
          onClick={() => setExpanded(true)}
          className="w-full cursor-zoom-in rounded-lg border border-neutral-200"
        />
      )}

      {expanded && src && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6"
          onClick={() => setExpanded(false)}
        >
          <img src={src} alt="Preview layar (diperbesar)" className="max-h-full max-w-full rounded-lg" />
        </div>
      )}
    </div>
  );
}
