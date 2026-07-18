import { useEffect, useState } from "react";
import { RefreshCw, ShieldAlert, Download } from "lucide-react";
import api, { API } from "@/lib/api";
import { AdminHeader } from "./AdminHeader";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";

const ENTITIES = ["all", "auth", "user", "client", "quote", "document", "service", "file", "settings"];
const ACTIONS = ["all", "login", "create", "update", "delete", "generate", "share", "password"];

const ACTION_STYLE = {
  login: "text-[#4A7C94] bg-[#4A7C94]/15",
  create: "text-emerald-300 bg-emerald-950/40",
  update: "text-amber-300 bg-amber-950/40",
  delete: "text-red-300 bg-red-950/40",
  generate: "text-[#A1A1AA] bg-[#1A1A1D]",
  share: "text-[#A1A1AA] bg-[#1A1A1D]",
  password: "text-purple-300 bg-purple-950/40",
};

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [entity, setEntity] = useState("all");
  const [action, setAction] = useState("all");
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    const params = new URLSearchParams({ limit: "200" });
    if (entity !== "all") params.set("entity", entity);
    if (action !== "all") params.set("action", action);
    api.get(`/audit?${params.toString()}`).then((r) => setLogs(r.data)).catch(() => setLogs([])).finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [entity, action]);

  const exportCsv = () => {
    const params = new URLSearchParams();
    if (entity !== "all") params.set("entity", entity);
    if (action !== "all") params.set("action", action);
    const token = localStorage.getItem("ed_token");
    fetch(`${API}/audit/export.csv?${params.toString()}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = "audit-log.csv"; a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => {});
  };

  return (
    <div>
      <AdminHeader title="Audit Log" subtitle="Who did what, and when — across the whole system">
        <button data-testid="audit-export" onClick={exportCsv}
          className="border border-[#27272A] hover:border-[#4A7C94] text-[#A1A1AA] hover:text-white px-4 py-2 rounded-sm text-sm flex items-center gap-2 transition-colors">
          <Download size={15} /> Export CSV
        </button>
        <button data-testid="audit-refresh" onClick={load}
          className="border border-[#27272A] hover:border-[#4A7C94] text-[#A1A1AA] hover:text-white px-4 py-2 rounded-sm text-sm flex items-center gap-2 transition-colors">
          <RefreshCw size={15} className={loading ? "animate-spin" : ""} /> Refresh
        </button>
      </AdminHeader>

      <div className="p-8 space-y-6">
        <div className="flex flex-wrap gap-4">
          <div className="w-48">
            <label className="label-caps block mb-2">Entity</label>
            <Select value={entity} onValueChange={setEntity}>
              <SelectTrigger data-testid="audit-filter-entity" className="bg-[#0A0A0B] border-[#27272A]"><SelectValue /></SelectTrigger>
              <SelectContent>{ENTITIES.map((e) => <SelectItem key={e} value={e}>{e === "all" ? "All entities" : e}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="w-48">
            <label className="label-caps block mb-2">Action</label>
            <Select value={action} onValueChange={setAction}>
              <SelectTrigger data-testid="audit-filter-action" className="bg-[#0A0A0B] border-[#27272A]"><SelectValue /></SelectTrigger>
              <SelectContent>{ACTIONS.map((a) => <SelectItem key={a} value={a}>{a === "all" ? "All actions" : a}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        </div>

        <div className="bg-[#121214] border border-[#27272A] rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#27272A] text-left text-[#71717A] text-xs uppercase tracking-wide">
                <th className="px-6 py-4">When</th><th className="px-6 py-4">User</th><th className="px-6 py-4">Action</th>
                <th className="px-6 py-4">Entity</th><th className="px-6 py-4">Detail</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 && (
                <tr><td colSpan={5} className="px-6 py-12 text-center text-[#71717A]">
                  <ShieldAlert size={22} className="mx-auto mb-2 opacity-50" /> No activity recorded for this filter yet.
                </td></tr>
              )}
              {logs.map((l) => (
                <tr key={l.id} data-testid={`audit-row-${l.id}`} className="border-b border-[#27272A]/60 hover:bg-[#1A1A1D]/40">
                  <td className="px-6 py-3 text-[#A1A1AA] whitespace-nowrap">{l.created_at ? new Date(l.created_at).toLocaleString() : "—"}</td>
                  <td className="px-6 py-3">{l.user_name || l.user_email || "System"}<div className="text-xs text-[#71717A]">{l.user_email}</div></td>
                  <td className="px-6 py-3"><span className={`px-2 py-1 rounded-sm text-xs ${ACTION_STYLE[l.action] || "text-[#A1A1AA] bg-[#1A1A1D]"}`}>{l.action}</span></td>
                  <td className="px-6 py-3 text-[#A1A1AA]">{l.entity}</td>
                  <td className="px-6 py-3 text-[#A1A1AA] max-w-xs truncate" title={l.detail || ""}>{l.detail || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
