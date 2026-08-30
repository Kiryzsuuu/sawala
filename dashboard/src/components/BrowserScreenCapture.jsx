import { useRef, useState } from "react";
import { MonitorUp, MonitorX } from "lucide-react";
import { authFetch } from "../auth";

const CAPTURE_INTERVAL_MS = 3000;

export default function BrowserScreenCapture() {
  const [active, setActive] = useState(false);
  const [error, setError] = useState("");
  const streamRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const timerRef = useRef(null);

  async function start() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: "window" },
        audio: false,
      });

      const video = document.createElement("video");
      video.srcObject = stream;
      video.muted = true;
      await video.play();

      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      streamRef.current = stream;
      videoRef.current = video;
      canvasRef.current = canvas;

      // Kalau host berhenti berbagi lewat dialog browser (bukan tombol kita),
      // pastikan state ikut berhenti juga.
      stream.getVideoTracks()[0].addEventListener("ended", stop);

      timerRef.current = setInterval(sendFrame, CAPTURE_INTERVAL_MS);
      setActive(true);
    } catch (err) {
      if (err.name !== "NotAllowedError") {
        setError("Gagal mengaktifkan screen capture: " + err.message);
      }
    }
  }

  async function sendFrame() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    if (!video.videoWidth || !video.videoHeight) return;

    // Resolusi video getDisplayMedia bisa berubah kapan saja (jendela yang
    // di-share di-resize/maximize) - samakan ukuran canvas ke resolusi
    // video saat ini tiap frame, supaya drawImage tidak men-stretch frame
    // ke ukuran canvas basi dan menghasilkan gambar pecah/distorsi.
    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      async (blob) => {
        if (!blob) return;
        const formData = new FormData();
        formData.append("file", blob, "screen.jpg");
        try {
          const res = await authFetch("/api/ingest/screen", {
            method: "POST",
            body: formData,
          });
          if (!res.ok) {
            const detail = await res.json().catch(() => null);
            setError(detail?.detail || `Server menolak frame (${res.status})`);
          } else {
            setError("");
          }
        } catch {
          setError("Tidak bisa menghubungi server.");
        }
      },
      "image/jpeg",
      0.8
    );
  }

  function stop() {
    clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    videoRef.current = null;
    canvasRef.current = null;
    setActive(false);
  }

  return (
    <div className="rounded-xl border border-line bg-card p-4">
      <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-ink-soft">
            {active ? <MonitorUp size={16} /> : <MonitorX size={16} />}
            Screen Capture via Browser
          </div>
          <p className="mt-1 text-xs text-neutral-500">
            Pakai ini kalau backend jalan di server/cloud (tidak punya akses layar lokal). Pilih jendela
            Zoom/Meet saat diminta browser. Perlu sesi aktif dulu.
          </p>
        </div>
        <button
          onClick={active ? stop : start}
          className="w-full flex-shrink-0 rounded-lg bg-ink-soft px-4 py-2 text-sm font-medium text-paper transition hover:bg-ink sm:w-auto"
        >
          {active ? "Hentikan" : "Aktifkan Screen Capture"}
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-neutral-500">{error}</p>}
    </div>
  );
}
