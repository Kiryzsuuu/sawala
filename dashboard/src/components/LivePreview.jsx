import { useEffect, useRef, useState } from "react";
import { ScanFace } from "lucide-react";
import { authFetch } from "../auth";

const POLL_INTERVAL_MS = 3000;

export default function LivePreview() {
  const [imageUrl, setImageUrl] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ok | empty | error
  const objectUrlRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await authFetch("/api/preview/last");
        if (cancelled) return;
        if (res.status === 404) {
          setStatus("empty");
          return;
        }
        if (!res.ok) {
          setStatus("error");
          return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = url;
        setImageUrl(url);
        setStatus("ok");
      } catch {
        if (!cancelled) setStatus("error");
      }
    }

    poll();
    const timer = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    };
  }, []);

  return (
    <div className="rounded-xl border border-line bg-card p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-ink-soft">
        <ScanFace size={16} />
        Preview Capture
      </div>
      <p className="mt-1 text-xs text-neutral-500">
        Ini persis frame yang dianalisis sistem, per kotak posisi di layar (bukan per akun Meet/Zoom
        - sistem tidak tahu nama asli peserta dari sini). Kotak hijau = sudah dikonfirmasi jadi
        peserta, abu-abu = terdeteksi tapi belum ada wajah.
      </p>

      <div className="mt-3 overflow-hidden rounded-lg border border-line bg-paper">
        {status === "ok" && imageUrl && (
          <img src={imageUrl} alt="Preview capture terakhir" className="w-full" />
        )}
        {status === "loading" && (
          <p className="p-6 text-center text-xs text-muted">Memuat preview...</p>
        )}
        {status === "empty" && (
          <p className="p-6 text-center text-xs text-muted">
            Belum ada frame yang diproses. Mulai sesi lalu aktifkan screen capture dulu.
          </p>
        )}
        {status === "error" && (
          <p className="p-6 text-center text-xs text-muted">Gagal memuat preview.</p>
        )}
      </div>
    </div>
  );
}
