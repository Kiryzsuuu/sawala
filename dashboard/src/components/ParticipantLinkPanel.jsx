import { useEffect, useState } from "react";
import { Copy, Check, Users } from "lucide-react";
import { API_BASE } from "../api";

export default function ParticipantLinkPanel() {
  const [link, setLink] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/network-info`)
      .then((res) => res.json())
      .then((data) => setLink(data.participant_link))
      .catch(() => setLink(""));
  }, []);

  if (!link) return null;

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard tidak tersedia, biarkan pengguna menyalin manual
    }
  }

  return (
    <div className="mb-6 rounded-xl border border-line bg-card p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-ink-soft">
        <Users size={16} />
        Link untuk Peserta
      </div>
      <p className="mt-1 text-xs text-neutral-500">
        Bagikan link ini ke peserta lain di jaringan/WiFi yang sama supaya mereka bisa melihat status monitor
        mereka sendiri saja.
      </p>
      <div className="mt-3 flex items-center gap-2">
        <code className="flex-1 truncate rounded-lg border border-line bg-paper px-3 py-2 text-xs text-ink-soft">
          {link}
        </code>
        <button
          onClick={copyLink}
          className="inline-flex items-center gap-1 rounded-lg bg-paper-alt px-3 py-2 text-xs text-ink-soft transition hover:bg-line"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
          {copied ? "Tersalin" : "Salin"}
        </button>
      </div>
    </div>
  );
}
