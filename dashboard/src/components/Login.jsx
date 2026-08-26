import { useState } from "react";
import { LogIn } from "lucide-react";
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
    <div className="flex min-h-screen items-center justify-center bg-paper px-4 font-sans text-ink">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center justify-center gap-3">
          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="Logo" className="h-10 w-10 object-cover" />
          <h1 className="text-xl font-bold">SAWALA</h1>
        </div>

        <form onSubmit={forgotMode ? handleForgot : handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-neutral-600">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-ink"
            />
          </div>

          {!forgotMode && (
            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-600">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-ink"
              />
            </div>
          )}

          {error && <p className="text-xs text-neutral-500">{error}</p>}
          {forgotMessage && <p className="text-xs text-neutral-500">{forgotMessage}</p>}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-ink px-4 py-2 text-sm font-medium text-ink hover:bg-ink hover:text-paper disabled:opacity-50"
          >
            <LogIn size={16} />
            {forgotMode ? "Kirim Link Reset" : "Masuk"}
          </button>

          <button
            type="button"
            onClick={() => {
              setForgotMode(!forgotMode);
              setError("");
              setForgotMessage("");
            }}
            className="w-full text-center text-xs text-neutral-500 hover:underline"
          >
            {forgotMode ? "Kembali ke halaman login" : "Lupa password?"}
          </button>
        </form>
      </div>
    </div>
  );
}
