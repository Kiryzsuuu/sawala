import { useEffect, useState } from "react";
import { Users, Trash2, Pencil, Plus, X } from "lucide-react";
import { authFetch } from "../auth";

function UserFormModal({ initial, onClose, onSaved }) {
  const isEdit = Boolean(initial);
  const [email, setEmail] = useState(initial?.email || "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState(initial?.role || "admin");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    const body = isEdit
      ? { ...(email !== initial.email ? { email } : {}), ...(password ? { password } : {}), role }
      : { email, password, role };

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
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-xl border border-neutral-300 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-ink">{isEdit ? "Edit User" : "Tambah User"}</h3>
          <button onClick={onClose}>
            <X size={16} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
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
          <div>
            <label className="mb-1 block text-xs font-medium text-neutral-600">
              Password {isEdit && "(kosongkan kalau tidak diganti)"}
            </label>
            <input
              type="password"
              required={!isEdit}
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-ink"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-neutral-600">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-ink"
            >
              <option value="admin">Admin</option>
              <option value="super_admin">Super Admin</option>
            </select>
          </div>
          {error && <p className="text-xs text-neutral-500">{error}</p>}
          <button
            type="submit"
            className="w-full rounded-lg border border-ink px-4 py-2 text-sm font-medium text-ink hover:bg-ink hover:text-paper"
          >
            Simpan
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
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-black/40 p-3 sm:p-6">
      <div className="w-full max-w-2xl rounded-xl border border-neutral-300 bg-white p-4 sm:p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <Users size={16} />
            Kelola User
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setModalUser(null)}
              className="inline-flex items-center gap-1 rounded-lg border border-ink px-3 py-1.5 text-xs text-ink hover:bg-ink hover:text-paper"
            >
              <Plus size={14} /> Tambah User
            </button>
            <button onClick={onClose}>
              <X size={18} />
            </button>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-neutral-500">Memuat...</p>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[480px] text-left text-xs">
            <thead>
              <tr className="border-b border-neutral-300 text-neutral-500">
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">Role</th>
                <th className="py-2 pr-4">Dibuat</th>
                <th className="py-2 pr-4"></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-neutral-200">
                  <td className="py-2 pr-4 text-ink">{u.email}</td>
                  <td className="py-2 pr-4 capitalize">{u.role.replace("_", " ")}</td>
                  <td className="py-2 pr-4 text-neutral-500">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : "-"}
                  </td>
                  <td className="py-2 pr-4">
                    <div className="flex gap-2">
                      <button onClick={() => setModalUser(u)} title="Edit">
                        <Pencil size={14} />
                      </button>
                      {u.id !== currentUserId && (
                        <button onClick={() => handleDelete(u)} title="Hapus">
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
