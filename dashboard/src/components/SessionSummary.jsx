import { Download } from "lucide-react";
import { authFetch } from "../auth";

async function downloadExport(path, filename) {
  const res = await authFetch(path);
  if (!res.ok) return;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function SessionSummary({ participants }) {
  return (
    <div className="rounded-xl border border-line bg-card p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink-soft">Ringkasan Sesi</h2>
        <div className="flex gap-2">
          <button
            onClick={() => downloadExport("/api/export/csv", "sawala-session.csv")}
            className="inline-flex items-center gap-1 rounded-lg bg-paper-alt px-3 py-1.5 text-xs text-ink-soft transition hover:bg-line"
          >
            <Download size={14} /> CSV
          </button>
          <button
            onClick={() => downloadExport("/api/export/json", "sawala-session.json")}
            className="inline-flex items-center gap-1 rounded-lg bg-paper-alt px-3 py-1.5 text-xs text-ink-soft transition hover:bg-line"
          >
            <Download size={14} /> JSON
          </button>
        </div>
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left text-xs text-neutral-600">
          <thead>
            <tr className="border-b border-line">
              <th className="py-2 pr-4">Peserta</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Flags</th>
            </tr>
          </thead>
          <tbody>
            {participants.map((p) => (
              <tr key={p.id} className="border-b border-neutral-200">
                <td className="py-2 pr-4 text-ink-soft">{p.name}</td>
                <td className="py-2 pr-4">{p.oncam ? "OnCam" : "OffCam"}</td>
                <td className="py-2 pr-4">{(p.flags || []).join(", ") || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
