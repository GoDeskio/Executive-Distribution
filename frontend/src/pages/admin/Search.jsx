import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Search as SearchIcon, Users, Inbox, FileText } from "lucide-react";
import api from "@/lib/api";
import { AdminHeader } from "./AdminHeader";

export default function Search() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [q, setQ] = useState(params.get("q") || "");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async (query) => {
    const term = (query ?? q).trim();
    if (!term) return;
    setBusy(true);
    setParams({ q: term });
    try { const { data } = await api.get(`/search?q=${encodeURIComponent(term)}`); setRes(data); }
    finally { setBusy(false); }
  };

  useEffect(() => { if (params.get("q")) run(params.get("q")); /* eslint-disable-next-line */ }, []);

  const count = res ? (res.clients.length + res.requests.length + res.documents.length) : 0;

  return (
    <div>
      <AdminHeader title="Search" subtitle="Client, phone, email, date, port, quote / PO / tracking number, item" />
      <div className="p-8 space-y-8">
        <div className="flex gap-2 max-w-2xl">
          <div className="flex-1 relative">
            <SearchIcon size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#71717A]" />
            <input data-testid="search-input" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && run()}
              placeholder="Search everything…" autoFocus
              className="w-full bg-[#121214] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm pl-10 pr-4 py-3 text-sm transition-colors" />
          </div>
          <button data-testid="search-btn" onClick={() => run()} className="bg-[#4A7C94] hover:bg-[#5A8CA4] text-white px-6 rounded-sm text-sm font-medium transition-colors">Search</button>
        </div>

        {busy && <p className="text-[#71717A] text-sm">Searching…</p>}
        {res && !busy && <p className="text-[#71717A] text-sm">{count} result{count !== 1 ? "s" : ""} for "{params.get("q")}"</p>}

        {res && (
          <div className="space-y-8">
            <Group icon={Inbox} title="Quote Requests" items={res.requests} render={(r) => (
              <div className="flex justify-between"><span className="font-medium">{r.name}</span><span className="text-[#71717A]">{r.email} · {r.destination}</span></div>
            )} onClick={() => navigate("/admin/crm")} />
            <Group icon={Users} title="Clients" items={res.clients} render={(c) => (
              <div className="flex justify-between"><span className="font-medium">{c.name}</span><span className="text-[#71717A]">{c.company} · {c.email || c.phone}</span></div>
            )} onClick={() => navigate("/admin/crm")} />
            <Group icon={FileText} title="Documents" items={res.documents} render={(d) => (
              <div className="flex justify-between"><span className="font-medium">{d.number} · {d.client_name}</span><span className="text-[#71717A]">{d.port} {d.po_number} {d.tracking_number}</span></div>
            )} onClick={() => navigate("/admin/documents")} />
          </div>
        )}
      </div>
    </div>
  );
}

function Group({ icon: Icon, title, items, render, onClick }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <div className="flex items-center gap-2 label-caps mb-3"><Icon size={14} /> {title} ({items.length})</div>
      <div className="bg-[#121214] border border-[#27272A] rounded-md divide-y divide-[#27272A]/60">
        {items.map((it) => (
          <button key={it.id} onClick={onClick} className="w-full text-left px-5 py-3 text-sm hover:bg-[#1A1A1D]/50 transition-colors">{render(it)}</button>
        ))}
      </div>
    </div>
  );
}
