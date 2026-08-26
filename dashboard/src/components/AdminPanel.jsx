import { useEffect, useState } from "react";
import { Users, Trash2, Pencil, Plus, X, UserPlus } from "lucide-react";
import { authFetch } from "../auth";

function UserFormModal({ initial, onClose, onSaved }) {
  const isEdit = Boolean(initial);
  const [email, setEmail] = useState(initial?.email || "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState(initial?.role || "admin");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const body = isEdit
      ? { ...(email !== initial.email ? { email } : {}), ...(password ? { password } : {}), role }
      : { email, password, role };

    try {
      const res = await authFetch(isEdit ? `/api/admin/users/${initial.id}` : "/api/admin/users", {
        method: isEdit ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Gagal menyimpan");
        return;
      }
      onSaved();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
      <div className="w-full max-w-sm rounded-2xl border border-line bg-card p-6 shadow-sm">
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <UserPlus size={16} />
            {isEdit ? "Edit User" : "Tambah User Baru"}
          </div>
          <button onClick={onClose} className="text-muted hover:text-ink">
            <X size={16} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-soft">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-sm text-ink outline-none transition focus:border-ink"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-soft">
              Password {isEdit && <span className="text-muted">(kosongkan kalau tidak diganti)</span>}
            </label>
            <input
              type="password"
              required={!isEdit}
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-sm text-ink outline-none transition focus:border-ink"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-soft">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-sm text-ink outline-none transition focus:border-ink"
            >
              <option value="admin">Admin</option>
              <option value="super_admin">Super Admin</option>
            </select>
          </div>
          {error && <p className="text-xs text-ink-soft">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-ink px-4 py-2.5 text-sm font-medium text-paper transition hover:bg-ink-soft disabled:opacity-50"
          >
            {loading ? "Menyimpan..." : "Simpan"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function AdminPanel({ currentUserId, onClose }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalUser, setModalUser] = useState(undefined); // undefined = closed, null = create, object = edit

  async function loadUsers() {
    setLoading(true);
    const res = await authFetch("/api/admin/users");
    const data = await res.json();
    setUsers(data.users || []);
    setLoading(false);
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function handleDelete(user) {
    if (!confirm(`Hapus user ${user.email}?`)) return;
    const res = await authFetch(`/api/admin/users/${user.id}`, { method: "DELETE" });
    if (res.ok) loadUsers();
  }

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-ink/40 p-3 sm:p-6">
      <div className="w-full max-w-2xl rounded-2xl border border-line bg-card p-5 shadow-sm sm:p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <Users size={16} />
            Kelola User
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setModalUser(null)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-ink px-3 py-2 text-xs font-medium text-paper transition hover:bg-ink-soft"
            >
              <Plus size={14} /> Tambah User
            </button>
            <button onClick={onClose} className="text-muted hover:text-ink">
              <X size={18} />
            </button>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-muted">Memuat...</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-line">
            <table className="w-full min-w-[480px] text-left text-xs">
              <thead>
                <tr className="border-b border-line bg-paper text-muted">
                  <th className="py-2.5 pl-4 pr-4 font-medium">Email</th>
                  <th className="py-2.5 pr-4 font-medium">Role</th>
                  <th className="py-2.5 pr-4 font-medium">Dibuat</th>
                  <th className="py-2.5 pr-4"></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-line last:border-0">
                    <td className="py-2.5 pl-4 pr-4 text-ink">{u.email}</td>
                    <td className="py-2.5 pr-4 capitalize text-ink-soft">{u.role.replace("_", " ")}</td>
                    <td className="py-2.5 pr-4 text-muted">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : "-"}
                    </td>
                    <td className="py-2.5 pr-4">
                      <div className="flex gap-3 text-muted">
                        <button onClick={() => setModalUser(u)} title="Edit" className="hover:text-ink">
                          <Pencil size={14} />
                        </button>
                        {u.id !== currentUserId && (
                          <button onClick={() => handleDelete(u)} title="Hapus" className="hover:text-ink">
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modalUser !== undefined && (
        <UserFormModal
          initial={modalUser}
          onClose={() => setModalUser(undefined)}
          onSaved={() => {
            setModalUser(undefined);
            loadUsers();
          }}
        />
      )}
    </div>
  );
}
