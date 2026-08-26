import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

function StatTile({ label, value }) {
  return (
    <div className="rounded-xl border border-line bg-card p-4">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
    </div>
  );
}

export default function LiveStats({ participants }) {
  const total = participants.length;
  const oncam = participants.filter((p) => p.oncam).length;
  const fatigued = participants.filter((p) => p.fatigue_detected).length;
  const withPhone = participants.filter((p) => p.holding_phone).length;

  const chartData = participants.map((p) => ({
    name: p.name?.split(" ")[0] || p.id,
    oncam_pct: total > 0 ? Math.round((p.oncam_duration_seconds || 0) / 10) : 0,
  }));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Total Peserta" value={total} />
        <StatTile label="OnCam" value={`${oncam}/${total}`} />
        <StatTile label="Fatigue Terdeteksi" value={fatigued} />
        <StatTile label="Pegang HP" value={withPhone} />
      </div>

      <div className="rounded-xl border border-line bg-card p-4">
        <p className="mb-2 text-xs text-neutral-500">Durasi OnCam per Peserta (menit)</p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e0d5" />
            <XAxis dataKey="name" stroke="#8a8577" fontSize={12} />
            <YAxis stroke="#8a8577" fontSize={12} />
            <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #d4cfc0", color: "#1a1a1a" }} />
            <Bar dataKey="oncam_pct" fill="#1a1a1a" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
