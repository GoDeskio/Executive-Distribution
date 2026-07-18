import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2, X, Shield, KeyRound, UserCog, Ban, CheckCircle2 } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { AdminHeader } from "./AdminHeader";

const inp = "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm transition-colors";
const PERM_LABELS = {
  dashboard: "Dashboard & Analytics", ai: "AI Assistant", documents: "Quotes & Docs",
  services: "Services", crm: "CRM", storage: "Object Storage", seo: "SEO Controls",
  settings: "Settings", search: "Search",
};

export default function Team() {
  const [users, setUsers] = useState([]);
  const [perms, setPerms] = useState([]);
  const [editing, setEditing] = useState(null);
  const [pwFor, setPwFor] = useState(null);
  const [newPw, setNewPw] = useState("");

  const load = () => api.get("/users").then((r) => setUsers(r.data)).catch(() => {});
  useEffect(() => { load(); api.get("/permissions").then((r) => setPerms(r.data.permissions)).catch(() => {}); }, []);

  const openNew = () => setEditing({ email: "", password: "", name: "", permissions: [] });

  const togglePerm = (p) => setEditing((e) => ({
    ...e, permissions: e.permissions.includes(p) ? e.permissions.filter((x) => x !== p) : [...e.permissions, p],
  }));

  const save = async () => {
    try {
      if (editing.id) {
        await api.put(`/users/${editing.id}`, { name: editing.name, permissions: editing.permissions, active: editing.active });
      } else {
        if (!editing.email.trim() || !editing.password.trim()) return toast.error("Email and password are required");
        await api.post("/users", { email: editing.email, password: editing.password, name: editing.name, permissions: editing.permissions });
      }
      toast.success("Sub-admin saved"); setEditing(null); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const toggleActive = async (u) => {
    await api.put(`/users/${u.id}`, { active: !(u.active !== false) });
    load(); toast.success(u.active !== false ? "Account disabled" : "Account enabled");
  };
  const remove = async (u) => { if (!window.confirm(`Remove ${u.name || u.email}?`)) return; await api.delete(`/users/${u.id}`); load(); toast.success("Removed"); };
  const resetPw = async () => {
    if (!newPw.trim()) return toast.error("Enter a new password");
    try { await api.post(`/users/${pwFor.id}/password`, { password: newPw }); toast.success("Password reset"); setPwFor(null); setNewPw(""); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div>
      <AdminHeader title="Team & Access" subtitle="Create sub-admins and control what each can access">
        <button data-testid="new-user-btn" onClick={openNew}
          className="bg-[#4A7C94] hover:bg-[#5A8CA4] text-white px-4 py-2 rounded-sm text-sm font-medium flex items-center gap-2 transition-colors">
          <Plus size={16} /> New Sub-admin
        </button>
      </AdminHeader>

      <div className="p-8">
        <div className="bg-[#121214] border border-[#27272A] rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-[#27272A] text-left text-[#71717A] text-xs uppercase tracking-wide">
              <th className="px-6 py-4">Name</th><th className="px-6 py-4">Email</th><th className="px-6 py-4">Role</th>
              <th className="px-6 py-4">Access</th><th className="px-6 py-4">Status</th><th className="px-6 py-4"></th>
            </tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} data-testid={`user-row-${u.id}`} className="border-b border-[#27272A]/60 hover:bg-[#1A1A1D]/40">
                  <td className="px-6 py-4 font-medium">{u.name}</td>
                  <td className="px-6 py-4 text-[#A1A1AA]">{u.email}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-sm ${u.role === "superadmin" ? "text-[#4A7C94] bg-[#4A7C94]/15" : "text-[#A1A1AA] bg-[#1A1A1D]"}`}>
                      <Shield size={11} /> {u.role === "superadmin" ? "Super Admin" : "Sub-admin"}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-xs text-[#A1A1AA] max-w-[220px]">
                    {u.role === "superadmin" ? "Full access" : (u.permissions?.length ? u.permissions.map((p) => PERM_LABELS[p] || p).join(", ") : "No sections")}
                  </td>
                  <td className="px-6 py-4">
                    {u.role === "superadmin" ? <span className="text-xs text-[#71717A]">—</span> :
                      <span className={`text-xs ${u.active !== false ? "text-emerald-400" : "text-red-400"}`}>{u.active !== false ? "Active" : "Disabled"}</span>}
                  </td>
                  <td className="px-6 py-4 text-right whitespace-nowrap">
                    {u.role !== "superadmin" && (
                      <>
                        <button data-testid={`edit-user-${u.id}`} onClick={() => setEditing({ ...u, password: "" })} title="Edit access" className="text-[#71717A] hover:text-white p-1 mr-1"><UserCog size={15} /></button>
                        <button data-testid={`reset-pw-btn-${u.id}`} onClick={() => setPwFor(u)} title="Reset password" className="text-[#71717A] hover:text-white p-1 mr-1"><KeyRound size={15} /></button>
                        <button data-testid={`toggle-active-${u.id}`} onClick={() => toggleActive(u)} title="Enable/disable" className="text-[#71717A] hover:text-amber-400 p-1 mr-1">{u.active !== false ? <Ban size={15} /> : <CheckCircle2 size={15} />}</button>
                        <button data-testid={`delete-user-${u.id}`} onClick={() => remove(u)} className="text-[#71717A] hover:text-red-400 p-1"><Trash2 size={15} /></button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {editing && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center overflow-y-auto p-6">
          <div className="bg-[#121214] border border-[#27272A] rounded-md w-full max-w-lg my-8">
            <div className="flex items-center justify-between p-6 border-b border-[#27272A]">
              <h2 className="font-display text-lg">{editing.id ? "Edit Sub-admin" : "New Sub-admin"}</h2>
              <button onClick={() => setEditing(null)} className="text-[#71717A] hover:text-white"><X size={20} /></button>
            </div>
            <div className="p-6 space-y-4">
              <div><label className="label-caps block mb-2">Name</label><input data-testid="user-name" value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} className={inp} /></div>
              {!editing.id && (
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="label-caps block mb-2">Email</label><input data-testid="user-email" value={editing.email} onChange={(e) => setEditing({ ...editing, email: e.target.value })} className={inp} /></div>
                  <div><label className="label-caps block mb-2">Password</label><input data-testid="user-password" type="text" value={editing.password} onChange={(e) => setEditing({ ...editing, password: e.target.value })} className={inp} /></div>
                </div>
              )}
              <div>
                <label className="label-caps block mb-3">Dashboard Sections They Can Access</label>
                <div className="grid grid-cols-2 gap-2">
                  {perms.map((p) => (
                    <label key={p} className={`flex items-center gap-2 text-sm border rounded-sm px-3 py-2 cursor-pointer transition-colors ${editing.permissions.includes(p) ? "border-[#4A7C94] bg-[#4A7C94]/10" : "border-[#27272A] hover:border-[#3f3f46]"}`}>
                      <input type="checkbox" data-testid={`perm-${p}`} checked={editing.permissions.includes(p)} onChange={() => togglePerm(p)} className="accent-[#4A7C94]" />
                      {PERM_LABELS[p] || p}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex gap-3 p-6 border-t border-[#27272A]">
              <button onClick={() => setEditing(null)} className="flex-1 border border-[#27272A] hover:bg-[#1A1A1D] rounded-sm py-2.5 text-sm transition-colors">Cancel</button>
              <button data-testid="save-user" onClick={save} className="flex-1 bg-[#4A7C94] hover:bg-[#5A8CA4] rounded-sm py-2.5 text-sm font-medium text-white transition-colors">Save</button>
            </div>
          </div>
        </div>
      )}

      {pwFor && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6">
          <div className="bg-[#121214] border border-[#27272A] rounded-md w-full max-w-sm p-6">
            <h2 className="font-display text-lg mb-4">Reset password — {pwFor.name}</h2>
            <input data-testid="reset-pw" type="text" value={newPw} onChange={(e) => setNewPw(e.target.value)} placeholder="New password" className={inp} />
            <div className="flex gap-3 mt-5">
              <button onClick={() => { setPwFor(null); setNewPw(""); }} className="flex-1 border border-[#27272A] hover:bg-[#1A1A1D] rounded-sm py-2.5 text-sm transition-colors">Cancel</button>
              <button data-testid="confirm-reset-pw" onClick={resetPw} className="flex-1 bg-[#4A7C94] hover:bg-[#5A8CA4] rounded-sm py-2.5 text-sm font-medium text-white transition-colors">Reset</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
