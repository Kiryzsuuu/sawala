import { useEffect, useState } from "react";
import { Camera, CameraOff, Smartphone, Smile, Ghost, Moon, Check } from "lucide-react";
import { useWebSocket } from "../hooks/useWebSocket";

const STORAGE_KEY = "meeting-monitor:my-participant-id";

function formatDuration(seconds) {
  const s = Math.floor(seconds || 0);
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m} menit ${rem} detik`;
}

const FLAG_LABELS = {
  AVATAR: { icon: Ghost, text: "Sistem mendeteksi kemungkinan kamera menampilkan foto/avatar, bukan wajah asli." },
  HOLDING_PHONE: { icon: Smartphone, text: "Terlihat sedang memegang ponsel." },
  FATIGUE: { icon: Moon, text: "Terlihat tanda kelelahan (mata sayu / kepala menunduk)." },
  ENGAGED: { icon: Smile, text: "Terlihat tersenyum / terlibat aktif." },
};

function readStoredId() {
  try {
    return localStorage.getItem(STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

function storeId(id) {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // localStorage tidak tersedia, lanjut tanpa mengingat pilihan
  }
}

export default function ParticipantSelfView() {
  const { participants, connected } = useWebSocket();
  const [selectedId, setSelectedId] = useState(readStoredId());

  useEffect(() => {
    if (selectedId) storeId(selectedId);
  }, [selectedId]);

  const me = participants.find((p) => p.id === selectedId);

  return (
    <div className="mx-auto min-h-screen max-w-md bg-paper px-5 py-8 font-sans text-ink">
      <div className="mb-6 text-center">
        <h1 className="text-lg font-bold">Status Monitor Saya</h1>
        <p className="mt-1 text-xs text-neutral-500">
          {connected ? "Terhubung ke host" : "Menyambung ke host..."}
        </p>
      </div>

      <div className="mb-6">
        <label className="mb-2 block text-xs font-medium text-neutral-600">Saya peserta yang mana?</label>
        <select
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          className="w-full rounded-lg border border-line bg-card px-3 py-2 text-sm text-ink"
        >
          <option value="">Pilih nama saya</option>
          {participants.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        {participants.length === 0 && (
          <p className="mt-2 text-xs text-neutral-400">
            Belum ada peserta terdeteksi. Pastikan kamera kamu menyala dan host sudah memulai sesi.
          </p>
        )}
      </div>

      {!selectedId && participants.length > 0 && (
        <p className="text-center text-sm text-neutral-500">Pilih nama kamu di atas untuk melihat status.</p>
      )}

      {selectedId && !me && (
        <p className="text-center text-sm text-neutral-500">
          Status kamu belum atau tidak lagi tersedia. Pastikan kamera menyala.
        </p>
      )}

      {me && (
        <div className="space-y-4">
          <div className="rounded-xl border border-line p-5 text-center">
            {me.oncam ? (
              <Camera className="mx-auto mb-2" size={28} />
            ) : (
              <CameraOff className="mx-auto mb-2" size={28} />
            )}
            <p className="text-xl font-semibold">{me.oncam ? "Kamera Menyala" : "Kamera Mati"}</p>
            <p className="mt-1 text-xs text-neutral-500">
              Total durasi oncam: {formatDuration(me.oncam_duration_seconds)}
            </p>
          </div>

          {(me.flags || []).length > 0 ? (
            <div className="space-y-2">
              {(me.flags || [])
                .filter((f) => f !== "OFFCAM" && FLAG_LABELS[f])
                .map((f) => {
                  const info = FLAG_LABELS[f];
                  const Icon = info.icon;
                  return (
                    <div key={f} className="flex items-start gap-2 rounded-lg border border-line p-3 text-sm">
                      <Icon size={16} className="mt-0.5 flex-shrink-0" />
                      <span>{info.text}</span>
                    </div>
                  );
                })}
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded-lg border border-line p-3 text-sm">
              <Check size={16} className="flex-shrink-0" />
              <span>Tidak ada catatan khusus saat ini.</span>
            </div>
          )}

          <p className="text-center text-xs text-neutral-400">
            Halaman ini hanya menampilkan status kamu sendiri. Diperbarui otomatis setiap beberapa detik.
          </p>
        </div>
      )}
    </div>
  );
}
