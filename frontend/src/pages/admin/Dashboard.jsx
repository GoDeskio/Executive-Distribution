import { useEffect, useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { Users, Eye, Briefcase, Package, Activity, Inbox, CheckCircle2, Bell, ScrollText, Download } from "lucide-react";
import api, { API } from "@/lib/api";
import { AdminHeader } from "./AdminHeader";
import { useAuth } from "@/context/AuthContext";
import { SoftwareUpdates } from "@/components/admin/SoftwareUpdates";
import { Backups } from "@/components/admin/Backups";

function Stat({ icon: Icon, label, value, accent }) {
  return (
    <div data-testid={`stat-${label.toLowerCase().replace(/\s/g, "-")}`}
      className="bg-[#121214] border border-[#27272A] rounded-md p-6">
      <div className="flex items-center justify-between mb-4">
        <span className="label-caps">{label}</span>
        <Icon size={18} className={accent ? "text-[#4A7C94]" : "text-[#71717A]"} strokeWidth={1.5} />
      </div>
      <div className="font-display text-3xl">{value}</div>
    </div>
  );
}

const PAGE_OPTIONS = [
  { path: "/", label: "Home" },
];

export default function Dashboard() {
  const [overview, setOverview] = useState({});
  const [series, setSeries] = useState([]);
  const [pages, setPages] = useState([]);
  const [heat, setHeat] = useState([]);
  const [heatPath, setHeatPath] = useState("/");
  const [pathOptions, setPathOptions] = useState(PAGE_OPTIONS);
  const [notifs, setNotifs] = useState([]);
  const [audit, setAudit] = useState([]);
  const { user } = useAuth();
  const isSuper = user?.role === "superadmin";

  useEffect(() => {
    api.get("/analytics/overview").then((r) => setOverview(r.data)).catch(() => {});
    api.get("/analytics/timeseries?days=14").then((r) => setSeries(r.data)).catch(() => {});
    api.get("/analytics/pages").then((r) => {
      setPages(r.data);
      const opts = r.data.map((p) => ({ path: p.path, label: p.path }));
      if (opts.length) setPathOptions(opts);
    }).catch(() => {});
    api.get("/notifications").then((r) => {
      setNotifs(r.data);
      if (r.data.some((n) => !n.read)) api.post("/notifications/read").catch(() => {});
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (isSuper) api.get("/audit?limit=10").then((r) => setAudit(r.data)).catch(() => {});
  }, [isSuper]);

  const exportAudit = () => {
    const token = localStorage.getItem("ed_token");
    fetch(`${API}/audit/export.csv`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = "audit-log.csv"; a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => {});
  };

  useEffect(() => {
    api.get(`/analytics/heatmap?path=${encodeURIComponent(heatPath)}`)
      .then((r) => setHeat(r.data)).catch(() => {});
  }, [heatPath]);

  return (
    <div>
      <AdminHeader title="Dashboard" subtitle="Visitor activity & business overview">
        <div className="flex items-center gap-2 text-sm text-[#4A7C94]">
          <Activity size={16} /> {overview.active_now || 0} active now
        </div>
      </AdminHeader>

      <div className="p-8 space-y-8">
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <Stat icon={Inbox} label="New Requests" value={overview.new_quotes ?? 0} accent />
          <Stat icon={Users} label="Total Visitors" value={overview.total_visitors ?? 0} />
          <Stat icon={Eye} label="Page Views" value={overview.total_views ?? 0} />
          <Stat icon={Briefcase} label="Clients" value={overview.total_clients ?? 0} />
          <Stat icon={Package} label="Services" value={overview.total_services ?? 0} />
        </div>

        {isSuper && <SoftwareUpdates />}
        {isSuper && <Backups />}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-[#121214] border border-[#27272A] rounded-md p-6">
            <div className="label-caps mb-6">Traffic — Last 14 Days</div>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={series}>
                <defs>
                  <linearGradient id="v" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4A7C94" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="#4A7C94" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272A" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "#71717A", fontSize: 11 }} tickFormatter={(d) => d.slice(5)} stroke="#27272A" />
                <YAxis tick={{ fill: "#71717A", fontSize: 11 }} stroke="#27272A" allowDecimals={false} />
                <Tooltip contentStyle={{ background: "#0A0A0B", border: "1px solid #27272A", borderRadius: 4, color: "#fff" }} />
                <Area type="monotone" dataKey="views" stroke="#4A7C94" strokeWidth={2} fill="url(#v)" name="Views" />
                <Area type="monotone" dataKey="visitors" stroke="#A1A1AA" strokeWidth={1.5} fillOpacity={0} name="Visitors" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-[#121214] border border-[#27272A] rounded-md p-6">
            <div className="label-caps mb-6">Top Pages</div>
            <div className="space-y-3">
              {pages.length === 0 && <p className="text-sm text-[#71717A]">No data yet.</p>}
              {pages.slice(0, 8).map((p) => (
                <div key={p.path} className="flex items-center justify-between text-sm">
                  <span className="text-[#A1A1AA] truncate max-w-[160px]">{p.path}</span>
                  <span className="text-white font-medium">{p.views}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RECENT ACTIVITY */}
        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6">
          <div className="flex items-center gap-2 label-caps mb-5"><Bell size={14} /> Recent Activity</div>
          {notifs.length === 0 ? (
            <p className="text-sm text-[#71717A]">No activity yet. Client quote approvals from the portal will appear here.</p>
          ) : (
            <div className="space-y-3">
              {notifs.slice(0, 8).map((n) => (
                <div key={n.id} data-testid={`notif-${n.id}`} className="flex items-center gap-3 text-sm border-b border-[#27272A]/50 pb-3 last:border-0">
                  <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                  <span className="flex-1"><span className="font-medium">{n.client_name}</span> approved quote <span className="font-mono text-xs text-[#4A7C94]">{n.document_number}</span></span>
                  <span className="text-xs text-[#71717A]">{n.created_at ? new Date(n.created_at).toLocaleString() : ""}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* SYSTEM ACTIVITY (audit) — superadmin only */}
        {isSuper && (
          <div data-testid="system-activity" className="bg-[#121214] border border-[#27272A] rounded-md p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2 label-caps"><ScrollText size={14} /> System Activity</div>
              <button data-testid="audit-export-csv" onClick={exportAudit}
                className="inline-flex items-center gap-2 border border-[#27272A] hover:border-[#4A7C94] text-[#A1A1AA] hover:text-white px-3 py-1.5 rounded-sm text-xs transition-colors">
                <Download size={13} /> Export CSV
              </button>
            </div>
            {audit.length === 0 ? (
              <p className="text-sm text-[#71717A]">No system activity recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {audit.slice(0, 10).map((a) => (
                  <div key={a.id} className="flex items-center gap-3 text-sm border-b border-[#27272A]/50 pb-3 last:border-0">
                    <span className="text-[#4A7C94] font-medium w-16 shrink-0">{a.action}</span>
                    <span className="flex-1 truncate"><span className="text-[#A1A1AA]">{a.user_email || "system"}</span> · {a.entity}{a.detail ? ` — ${a.detail}` : ""}</span>
                    <span className="text-xs text-[#71717A] shrink-0">{a.created_at ? new Date(a.created_at).toLocaleString() : ""}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* HEATMAP */}
        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="label-caps">Click Heatmap</div>
            <select data-testid="heatmap-path-select" value={heatPath} onChange={(e) => setHeatPath(e.target.value)}
              className="bg-[#0A0A0B] border border-[#27272A] rounded-sm px-3 py-1.5 text-sm outline-none focus:border-[#4A7C94]">
              {pathOptions.map((o) => <option key={o.path} value={o.path}>{o.label}</option>)}
            </select>
          </div>
          <div data-testid="heatmap-canvas" className="relative w-full rounded-sm border border-[#27272A] overflow-hidden bg-[#0A0A0B]"
            style={{ height: 420 }}>
            <div className="absolute inset-0 opacity-10"
              style={{ backgroundImage: "linear-gradient(#27272A 1px,transparent 1px),linear-gradient(90deg,#27272A 1px,transparent 1px)", backgroundSize: "40px 40px" }} />
            {heat.map((pt, i) => (
              <div key={i} className="absolute rounded-full pointer-events-none"
                style={{
                  left: `${pt.x * 100}%`, top: `${Math.min(pt.y, 1) * 100}%`,
                  width: 46, height: 46, transform: "translate(-50%,-50%)",
                  background: "radial-gradient(circle, rgba(74,124,148,0.55) 0%, rgba(74,124,148,0) 70%)",
                  mixBlendMode: "screen",
                }} />
            ))}
            {heat.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center text-[#71717A] text-sm">
                No click activity recorded for this page yet.
              </div>
            )}
          </div>
          <p className="text-xs text-[#71717A] mt-3">{heat.length} clicks mapped. Warmer clusters indicate higher visitor engagement.</p>
        </div>
      </div>
    </div>
  );
}
