import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2, X, Users, Globe, FileText, Upload, Download, Building2, Mail, Phone, Inbox, MapPin } from "lucide-react";
import api, { fileUrl, formatApiError } from "@/lib/api";
import { AdminHeader } from "./AdminHeader";

const inp = "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm transition-colors";
const STATUS = { lead: "text-[#A1A1AA] bg-[#1A1A1D]", active: "text-emerald-300 bg-emerald-950/40", vip: "text-[#4A7C94] bg-[#4A7C94]/15", inactive: "text-[#71717A] bg-[#121214]" };
const QSTATUS = { new: "text-amber-300 bg-amber-950/40", reviewing: "text-[#4A7C94] bg-[#4A7C94]/15", quoted: "text-emerald-300 bg-emerald-950/40", closed: "text-[#71717A] bg-[#121214]" };

export default function CRM() {
  const [tab, setTab] = useState("requests");
  return (
    <div>
      <AdminHeader title="CRM" subtitle="Quote requests, clients, visitors & documents" />
      <div className="px-8 pt-6">
        <div className="flex gap-1 border-b border-[#27272A]">
          {[["requests", "Quote Requests", Inbox], ["clients", "Clients", Users], ["visitors", "Visitors", Globe], ["documents", "Documents", FileText]].map(([k, l, Icon]) => (
            <button key={k} data-testid={`crm-tab-${k}`} onClick={() => setTab(k)}
              className={`flex items-center gap-2 px-5 py-3 text-sm border-b-2 -mb-px transition-colors ${tab === k ? "border-[#4A7C94] text-[#4A7C94]" : "border-transparent text-[#A1A1AA] hover:text-white"}`}>
              <Icon size={15} /> {l}
            </button>
          ))}
        </div>
      </div>
      <div className="p-8">
        {tab === "requests" && <Requests />}
        {tab === "clients" && <Clients />}
        {tab === "visitors" && <Visitors />}
        {tab === "documents" && <Documents />}
      </div>
    </div>
  );
}

function Requests() {
  const [quotes, setQuotes] = useState([]);
  const load = () => api.get("/quotes").then((r) => setQuotes(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const setStatus = async (id, status) => {
    await api.put(`/quotes/${id}`, { status });
    setQuotes((q) => q.map((x) => (x.id === id ? { ...x, status } : x)));
    toast.success("Status updated");
  };
  const remove = async (id) => { if (!window.confirm("Delete this request?")) return; await api.delete(`/quotes/${id}`); load(); toast.success("Deleted"); };
  const convert = async (q) => {
    try {
      await api.post("/clients", { name: q.name, company: q.company, email: q.email, phone: q.phone, status: "lead", value: 0, tags: ["from-quote"], notes: `Destination: ${q.destination}\n\n${q.description}` });
      await api.put(`/quotes/${q.id}`, { status: "quoted" });
      load();
      toast.success("Added to Clients pipeline");
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail) || "Could not convert request");
    }
  };

  if (quotes.length === 0)
    return <div className="bg-[#121214] border border-[#27272A] rounded-md p-16 text-center text-[#71717A]">
      <Inbox size={40} className="mx-auto mb-4 opacity-50" /><p>No quote requests yet. Submissions from the website "Request a Quote" form appear here.</p>
    </div>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      {quotes.map((q) => (
        <div key={q.id} data-testid={`quote-card-${q.id}`} className="bg-[#121214] border border-[#27272A] rounded-md p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <div className="flex items-center gap-3">
                <h3 className="font-display text-lg">{q.name}</h3>
                <span className={`px-2 py-0.5 rounded-sm text-xs ${QSTATUS[q.status] || QSTATUS.new}`}>{q.status}</span>
              </div>
              <div className="text-xs text-[#71717A] mt-1">{q.created_at ? new Date(q.created_at).toLocaleString() : ""}</div>
            </div>
            <button data-testid={`delete-quote-${q.id}`} onClick={() => remove(q.id)} className="text-[#71717A] hover:text-red-400"><Trash2 size={16} /></button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm mb-4">
            <Info icon={Mail} value={q.email} />
            {q.company && <Info icon={Building2} value={q.company} />}
            {q.phone && <Info icon={Phone} value={q.phone} />}
            {q.destination && <Info icon={MapPin} value={q.destination} />}
          </div>

          {q.description && (
            <div className="bg-[#0A0A0B] border border-[#27272A] rounded-sm p-4 text-sm text-[#A1A1AA] mb-4 whitespace-pre-line">{q.description}</div>
          )}

          {q.images?.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {q.images.map((img, i) => (
                <a key={i} href={fileUrl(img)} target="_blank" rel="noreferrer"
                  className="h-16 w-16 rounded-sm overflow-hidden border border-[#27272A] hover:border-[#4A7C94] transition-colors">
                  <img src={fileUrl(img)} alt="" className="h-full w-full object-cover" />
                </a>
              ))}
            </div>
          )}

          <div className="flex items-center gap-2 pt-4 border-t border-[#27272A]">
            <select data-testid={`quote-status-${q.id}`} value={q.status} onChange={(e) => setStatus(q.id, e.target.value)}
              className="bg-[#0A0A0B] border border-[#27272A] rounded-sm px-3 py-2 text-xs outline-none focus:border-[#4A7C94]">
              <option value="new">New</option><option value="reviewing">Reviewing</option><option value="quoted">Quoted</option><option value="closed">Closed</option>
            </select>
            <button data-testid={`convert-quote-${q.id}`} onClick={() => convert(q)}
              className="ml-auto text-xs bg-[#4A7C94] hover:bg-[#5A8CA4] text-white px-3 py-2 rounded-sm transition-colors flex items-center gap-1">
              <Users size={13} /> Add to Clients
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function Info({ icon: Icon, value }) {
  return <div className="flex items-center gap-2 text-[#A1A1AA] min-w-0"><Icon size={14} className="text-[#4A7C94] shrink-0" /><span className="truncate">{value}</span></div>;
}

function Clients() {
  const [clients, setClients] = useState([]);
  const [editing, setEditing] = useState(null);
  const EMPTY = { name: "", company: "", email: "", phone: "", status: "lead", value: 0, tags: [], notes: "" };

  const load = () => api.get("/clients").then((r) => setClients(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!editing.name.trim()) return toast.error("Name required");
    const payload = { ...editing, value: +editing.value || 0 };
    delete payload.id; delete payload.created_at;
    try {
      if (editing.id) await api.put(`/clients/${editing.id}`, payload);
      else await api.post("/clients", payload);
      toast.success("Client saved"); setEditing(null); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const remove = async (id) => { if (!window.confirm("Delete client?")) return; await api.delete(`/clients/${id}`); load(); toast.success("Deleted"); };

  return (
    <div>
      <div className="flex justify-end mb-4">
        <button data-testid="new-client-btn" onClick={() => setEditing({ ...EMPTY })}
          className="bg-[#4A7C94] hover:bg-[#5A8CA4] text-white px-4 py-2 rounded-sm text-sm font-medium flex items-center gap-2 transition-colors">
          <Plus size={16} /> Add Client
        </button>
      </div>
      <div className="bg-[#121214] border border-[#27272A] rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#27272A] text-left text-[#71717A] text-xs uppercase tracking-wide">
              <th className="px-6 py-4">Name</th><th className="px-6 py-4">Company</th><th className="px-6 py-4">Contact</th>
              <th className="px-6 py-4">Status</th><th className="px-6 py-4">Value</th><th className="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody>
            {clients.length === 0 && <tr><td colSpan={6} className="px-6 py-10 text-center text-[#71717A]">No clients yet.</td></tr>}
            {clients.map((c) => (
              <tr key={c.id} data-testid={`client-row-${c.id}`} className="border-b border-[#27272A]/60 hover:bg-[#1A1A1D]/40 cursor-pointer" onClick={() => setEditing({ ...c })}>
                <td className="px-6 py-4 font-medium">{c.name}</td>
                <td className="px-6 py-4 text-[#A1A1AA]">{c.company || "—"}</td>
                <td className="px-6 py-4 text-[#A1A1AA]">{c.email || c.phone || "—"}</td>
                <td className="px-6 py-4"><span className={`px-2 py-1 rounded-sm text-xs ${STATUS[c.status] || STATUS.lead}`}>{c.status}</span></td>
                <td className="px-6 py-4">${(c.value || 0).toLocaleString()}</td>
                <td className="px-6 py-4 text-right"><button data-testid={`delete-client-${c.id}`} onClick={(e) => { e.stopPropagation(); remove(c.id); }} className="text-[#71717A] hover:text-red-400"><Trash2 size={15} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center overflow-y-auto p-6">
          <div className="bg-[#121214] border border-[#27272A] rounded-md w-full max-w-lg my-8">
            <div className="flex items-center justify-between p-6 border-b border-[#27272A]">
              <h2 className="font-display text-lg">{editing.id ? "Edit Client" : "New Client"}</h2>
              <button onClick={() => setEditing(null)} className="text-[#71717A] hover:text-white"><X size={20} /></button>
            </div>
            <div className="p-6 space-y-4">
              <F l="Name"><input data-testid="client-name" value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} className={inp} /></F>
              <div className="grid grid-cols-2 gap-4">
                <F l="Company"><input value={editing.company} onChange={(e) => setEditing({ ...editing, company: e.target.value })} className={inp} /></F>
                <F l="Deal Value ($)"><input type="number" value={editing.value} onChange={(e) => setEditing({ ...editing, value: e.target.value })} className={inp} /></F>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <F l="Email"><input value={editing.email} onChange={(e) => setEditing({ ...editing, email: e.target.value })} className={inp} /></F>
                <F l="Phone"><input value={editing.phone} onChange={(e) => setEditing({ ...editing, phone: e.target.value })} className={inp} /></F>
              </div>
              <F l="Status">
                <select value={editing.status} onChange={(e) => setEditing({ ...editing, status: e.target.value })} className={inp}>
                  <option value="lead">Lead</option><option value="active">Active</option><option value="vip">VIP</option><option value="inactive">Inactive</option>
                </select>
              </F>
              <F l="Notes"><textarea rows={3} value={editing.notes} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} className={inp} /></F>
            </div>
            <div className="flex gap-3 p-6 border-t border-[#27272A]">
              <button onClick={() => setEditing(null)} className="flex-1 border border-[#27272A] hover:bg-[#1A1A1D] rounded-sm py-2.5 text-sm transition-colors">Cancel</button>
              <button data-testid="save-client" onClick={save} className="flex-1 bg-[#4A7C94] hover:bg-[#5A8CA4] rounded-sm py-2.5 text-sm font-medium text-white transition-colors">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Visitors() {
  const [visitors, setVisitors] = useState([]);
  useEffect(() => { api.get("/analytics/visitors").then((r) => setVisitors(r.data)).catch(() => {}); }, []);
  return (
    <div className="bg-[#121214] border border-[#27272A] rounded-md overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#27272A] text-left text-[#71717A] text-xs uppercase tracking-wide">
            <th className="px-6 py-4">Session</th><th className="px-6 py-4">Device</th><th className="px-6 py-4">Views</th>
            <th className="px-6 py-4">Last Page</th><th className="px-6 py-4">First Seen</th><th className="px-6 py-4">Last Seen</th>
          </tr>
        </thead>
        <tbody>
          {visitors.length === 0 && <tr><td colSpan={6} className="px-6 py-10 text-center text-[#71717A]">No visitors tracked yet.</td></tr>}
          {visitors.map((v) => (
            <tr key={v.id} data-testid={`visitor-row-${v.session_id}`} className="border-b border-[#27272A]/60 hover:bg-[#1A1A1D]/40">
              <td className="px-6 py-4 font-mono text-xs text-[#A1A1AA]">{v.session_id?.slice(0, 14)}…</td>
              <td className="px-6 py-4 capitalize">{v.device}</td>
              <td className="px-6 py-4">{v.page_views || 0}</td>
              <td className="px-6 py-4 text-[#A1A1AA]">{v.last_path || "—"}</td>
              <td className="px-6 py-4 text-[#71717A] text-xs">{v.first_seen ? new Date(v.first_seen).toLocaleString() : "—"}</td>
              <td className="px-6 py-4 text-[#71717A] text-xs">{v.last_seen ? new Date(v.last_seen).toLocaleString() : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Documents() {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const load = () => api.get("/files?category=document").then((r) => setDocs(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const upload = async (file) => {
    setUploading(true);
    const fd = new FormData(); fd.append("file", file); fd.append("category", "document");
    try { await api.post("/files/upload", fd); toast.success("Uploaded"); load(); }
    catch (e) { toast.error("Upload failed"); } finally { setUploading(false); }
  };
  const remove = async (id) => { if (!window.confirm("Delete document?")) return; await api.delete(`/files/${id}`); load(); toast.success("Deleted"); };

  return (
    <div>
      <div className="flex justify-end mb-4">
        <label className="bg-[#4A7C94] hover:bg-[#5A8CA4] text-white px-4 py-2 rounded-sm text-sm font-medium flex items-center gap-2 cursor-pointer transition-colors">
          <Upload size={16} /> {uploading ? "Uploading…" : "Upload Document"}
          <input data-testid="doc-upload" type="file" className="hidden" onChange={(e) => e.target.files[0] && upload(e.target.files[0])} />
        </label>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {docs.length === 0 && <p className="text-[#71717A] text-sm col-span-full">No documents uploaded.</p>}
        {docs.map((d) => (
          <div key={d.id} data-testid={`doc-${d.id}`} className="bg-[#121214] border border-[#27272A] rounded-md p-5 flex items-start justify-between">
            <div className="flex items-start gap-3 min-w-0">
              <FileText size={20} className="text-[#4A7C94] shrink-0 mt-1" strokeWidth={1.5} />
              <div className="min-w-0">
                <div className="text-sm truncate">{d.original_filename}</div>
                <div className="text-xs text-[#71717A]">{(d.size / 1024).toFixed(0)} KB</div>
              </div>
            </div>
            <div className="flex gap-1 shrink-0">
              <a href={fileUrl(d.url)} target="_blank" rel="noreferrer" className="text-[#71717A] hover:text-white p-1"><Download size={15} /></a>
              <button onClick={() => remove(d.id)} className="text-[#71717A] hover:text-red-400 p-1"><Trash2 size={15} /></button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function F({ l, children }) {
  return <div><label className="label-caps block mb-2">{l}</label>{children}</div>;
}
