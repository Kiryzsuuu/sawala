import { Camera, CameraOff, Smartphone, Smile, Ghost, Moon } from "lucide-react";

function Badge({ icon: Icon, label }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-ink px-2 py-0.5 text-xs font-medium text-ink">
      <Icon size={12} />
      {label}
    </span>
  );
}

function formatDuration(seconds) {
  const s = Math.floor(seconds || 0);
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

export default function ParticipantCard({ participant }) {
  const p = participant;
  const flags = p.flags || [];

  return (
    <div className="rounded-xl border border-line bg-card p-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-ink">{p.name}</h3>
          <p className="text-xs text-neutral-500">{p.id}</p>
        </div>
        {p.oncam ? (
          <Badge icon={Camera} label="OnCam" />
        ) : (
          <Badge icon={CameraOff} label="OffCam" />
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {flags.includes("AVATAR") && <Badge icon={Ghost} label="Avatar" />}
        {flags.includes("HOLDING_PHONE") && <Badge icon={Smartphone} label="Pegang HP" />}
        {flags.includes("FATIGUE") && <Badge icon={Moon} label="Fatigue" />}
        {flags.includes("ENGAGED") && <Badge icon={Smile} label="Engaged" />}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-neutral-500">
        <div>
          <span className="block text-neutral-400">Durasi OnCam</span>
          <span className="text-ink">{formatDuration(p.oncam_duration_seconds)}</span>
        </div>
        <div>
          <span className="block text-neutral-400">Emosi</span>
          <span className="text-ink capitalize">{p.dominant_emotion || "-"}</span>
        </div>
        <div>
          <span className="block text-neutral-400">EAR</span>
          <span className="text-ink">{p.ear_value ?? "-"}</span>
        </div>
        <div>
          <span className="block text-neutral-400">Liveness</span>
          <span className="text-ink">{p.liveness_score ?? "-"}</span>
        </div>
      </div>
    </div>
  );
}
