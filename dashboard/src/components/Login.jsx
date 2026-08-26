import { useState } from "react";
import { LogIn, Mail } from "lucide-react";
import { API_BASE } from "../api";
import { saveSession } from "../auth";

export default function Login({ onLoggedIn }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [forgotMode, setForgotMode] = useState(false);
  const [forgotMessage, setForgotMessage] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Login gagal");
        return;
      }
      saveSession(data.access_token, data.user);
      onLoggedIn(data.user);
    } catch {
      setError("Tidak bisa menghubungi server.");
    } finally {
      setLoading(false);
    }
  }

  async function handleForgot(e) {
    e.preventDefault();
    setError("");
    setForgotMessage("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      setForgotMessage(data.message || "Kalau email terdaftar, link reset sudah dikirim.");
    } catch {
      setError("Tidak bisa menghubungi server.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-4 py-10 font-sans text-ink-soft">
      <div className="w-full max-w-sm rounded-2xl border border-line bg-card p-8 shadow-sm">
        <div className="mb-7 flex flex-col items-center text-center">
          <img
            src={`${import.meta.env.BASE_URL}logo.png`}
            alt="SAWALA"
            className="mb-3 h-11 w-11 rounded-xl object-cover"
          />
          <h1 className="text-lg font-semibold">SAWALA</h1>
          <p className="mt-1 text-xs text-muted">
            {forgotMode ? "Masukkan email untuk reset password" : "Masuk ke dashboard monitoring"}
          </p>
        </div>

        <form onSubmit={forgotMode ? handleForgot : handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-soft">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-sm text-ink-soft outline-none transition focus:border-ink-soft"
            />
          </div>

          {!forgotMode && (
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label className="block text-xs font-medium text-ink-soft">Password</label>
                <button
                  type="button"
                  onClick={() => {
                    setForgotMode(true);
                    setError("");
                    setForgotMessage("");
                  }}
                  className="text-xs text-muted hover:text-ink hover:underline"
                >
                  Lupa password?
                </button>
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-sm text-ink-soft outline-none transition focus:border-ink-soft"
              />
            </div>
          )}

          {error && <p className="text-xs text-ink-soft">{error}</p>}
          {forgotMessage && <p className="text-xs text-ink-soft">{forgotMessage}</p>}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-ink-soft px-4 py-2.5 text-sm font-medium text-paper transition hover:bg-ink disabled:opacity-50"
          >
            {forgotMode ? <Mail size={16} /> : <LogIn size={16} />}
            {loading ? "Memproses..." : forgotMode ? "Kirim Link Reset" : "Masuk"}
          </button>

          {forgotMode && (
            <button
              type="button"
              onClick={() => {
                setForgotMode(false);
                setError("");
                setForgotMessage("");
              }}
              className="w-full text-center text-xs text-muted hover:text-ink hover:underline"
            >
              Kembali ke halaman login
            </button>
          )}
        </form>

        <p className="mt-6 text-center text-xs text-muted">
          Belum punya akun? Hubungi admin untuk dibuatkan akses.
        </p>
      </div>
    </div>
  );
}
