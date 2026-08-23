import { Download } from "lucide-react";
import { API_BASE } from "../api";

export default function SessionSummary({ participants }) {
  return (
    <div className="rounded-xl border border-neutral-300 bg-white p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink">Ringkasan Sesi</h2>
        <div className="flex gap-2">
          <a
            href={`${API_BASE}/api/export/csv`}
            className="inline-flex items-center gap-1 rounded-lg border border-ink px-3 py-1.5 text-xs text-ink hover:bg-ink hover:text-paper"
          >
            <Download size={14} /> CSV
          </a>
          <a
            href={`${API_BASE}/api/export/json`}
            className="inline-flex items-center gap-1 rounded-lg border border-ink px-3 py-1.5 text-xs text-ink hover:bg-ink hover:text-paper"
          >
            <Download size={14} /> JSON
          </a>
        </div>
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left text-xs text-neutral-600">
          <thead>
            <tr className="border-b border-neutral-300">
              <th className="py-2 pr-4">Peserta</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Flags</th>
            </tr>
          </thead>
          <tbody>
            {participants.map((p) => (
              <tr key={p.id} className="border-b border-neutral-200">
                <td className="py-2 pr-4 text-ink">{p.name}</td>
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
