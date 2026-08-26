import { useState } from "react";
import { KeyRound } from "lucide-react";
import { API_BASE } from "../api";

export default function ResetPassword() {
  const token = new URLSearchParams(window.location.search).get("token") || "";
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus(data.detail || "Gagal reset password");
        return;
      }
      setDone(true);
    } catch {
      setStatus("Tidak bisa menghubungi server.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-4 py-10 font-sans text-ink">
      <div className="w-full max-w-sm rounded-2xl border border-line bg-card p-8 shadow-sm">
        <div className="mb-7 flex flex-col items-center text-center">
          <img
            src={`${import.meta.env.BASE_URL}logo.png`}
            alt="SAWALA"
            className="mb-3 h-11 w-11 rounded-xl object-cover"
          />
          <h1 className="text-lg font-semibold">Reset Password</h1>
          <p className="mt-1 text-xs text-muted">Buat password baru untuk akun SAWALA kamu.</p>
        </div>

        {!token ? (
          <p className="text-center text-sm text-ink-soft">
            Link reset password tidak valid atau sudah kedaluwarsa. Minta link baru lewat
            halaman login.
          </p>
        ) : done ? (
          <div className="text-center">
            <p className="mb-5 text-sm text-ink-soft">
              Password berhasil diganti. Silakan masuk lagi dengan password baru kamu.
            </p>
            <a
              href="/app/"
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-ink px-4 py-2.5 text-sm font-medium text-paper transition hover:bg-ink-soft"
            >
              Ke Halaman Login
            </a>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink-soft">Password Baru</label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-sm text-ink outline-none transition focus:border-ink"
              />
            </div>
            {status && <p className="text-xs text-ink-soft">{status}</p>}
            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-ink px-4 py-2.5 text-sm font-medium text-paper transition hover:bg-ink-soft disabled:opacity-50"
            >
              <KeyRound size={16} />
              {loading ? "Memproses..." : "Ganti Password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
