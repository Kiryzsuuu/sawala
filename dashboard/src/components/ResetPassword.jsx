import { useState } from "react";
import { KeyRound } from "lucide-react";
import { API_BASE } from "../api";

export default function ResetPassword() {
  const token = new URLSearchParams(window.location.search).get("token") || "";
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [done, setDone] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus("");
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
    }
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper px-4 font-sans text-ink">
        <p className="text-sm text-neutral-500">Link reset password tidak valid.</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-4 font-sans text-ink">
      <div className="w-full max-w-sm">
        <h1 className="mb-6 text-center text-xl font-bold">Reset Password</h1>

        {done ? (
          <p className="text-center text-sm text-neutral-600">
            Password berhasil diganti. Silakan{" "}
            <a href="/" className="underline">
              login
            </a>{" "}
            dengan password baru.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-600">Password Baru</label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-ink"
              />
            </div>
            {status && <p className="text-xs text-neutral-500">{status}</p>}
            <button
              type="submit"
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-ink px-4 py-2 text-sm font-medium text-ink hover:bg-ink hover:text-paper"
            >
              <KeyRound size={16} />
              Ganti Password
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
