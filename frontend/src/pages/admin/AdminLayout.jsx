import { NavLink, useNavigate, Outlet } from "react-router-dom";
import {
  LayoutDashboard, Package, Users, HardDrive, Search as SearchIcon, Settings as SettingsIcon,
  User, LogOut, Ship, Sparkles, FileText, Bell, Shield, ScrollText, AlertTriangle,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { fileUrl } from "@/lib/api";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";

const NAV = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true, perm: "dashboard" },
  { to: "/admin/ai", label: "AI Assistant", icon: Sparkles, perm: "ai" },
  { to: "/admin/documents", label: "Quotes & Docs", icon: FileText, perm: "documents" },
  { to: "/admin/services", label: "Services", icon: Package, perm: "services" },
  { to: "/admin/crm", label: "CRM", icon: Users, perm: "crm" },
  { to: "/admin/storage", label: "Object Storage", icon: HardDrive, perm: "storage" },
  { to: "/admin/seo", label: "SEO Controls", icon: SearchIcon, perm: "seo" },
  { to: "/admin/team", label: "Team & Access", icon: Shield, superOnly: true },
  { to: "/admin/audit", label: "Audit Log", icon: ScrollText, superOnly: true },
  { to: "/admin/settings", label: "Settings", icon: SettingsIcon, perm: "settings" },
  { to: "/admin/profile", label: "Profile", icon: User },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [company, setCompany] = useState("Executive Distribution");
  const [logo, setLogo] = useState("");
  const [q, setQ] = useState("");
  const [unread, setUnread] = useState(0);
  const [updateInfo, setUpdateInfo] = useState(null);

  useEffect(() => {
    api.get("/settings").then((r) => {
      if (r.data.company_name) setCompany(r.data.company_name);
      if (r.data.logo_url) setLogo(r.data.logo_url);
    }).catch(() => {});
  }, []);

  const isSuper = user?.role === "superadmin";

  useEffect(() => {
    if (!isSuper) return;
    api.get("/updates/status").then((r) => setUpdateInfo(r.data)).catch(() => {});
  }, [isSuper]);

  useEffect(() => {
    const fetchCount = () => api.get("/notifications/unread-count").then((r) => setUnread(r.data.count)).catch(() => {});
    fetchCount();
    const t = setInterval(fetchCount, 30000);
    return () => clearInterval(t);
  }, []);

  const doLogout = () => { logout(); navigate("/login"); };
  const doSearch = (e) => { e.preventDefault(); if (q.trim()) navigate(`/admin/search?q=${encodeURIComponent(q.trim())}`); };

  const canSee = (n) => {
    if (n.superOnly) return isSuper;
    if (!n.perm) return true; // profile always
    return isSuper || (user?.permissions || []).includes(n.perm);
  };
  const visibleNav = NAV.filter(canSee);

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex">
      <aside className="w-64 shrink-0 border-r border-[#27272A] bg-[#0A0A0B] fixed inset-y-0 left-0 flex flex-col z-40">
        <div className="h-20 flex items-center gap-3 px-6 border-b border-[#27272A]">
          {logo ? (
            <img src={fileUrl(logo)} alt="logo" className="h-8 w-auto object-contain" />
          ) : (
            <div className="h-8 w-8 border border-[#4A7C94] flex items-center justify-center">
              <Ship size={16} className="text-[#4A7C94]" strokeWidth={1.5} />
            </div>
          )}
          <span className="font-display text-sm leading-tight truncate">{company}</span>
          <button data-testid="notif-bell" onClick={() => navigate("/admin")} title="Notifications"
            className="ml-auto relative text-[#A1A1AA] hover:text-white transition-colors">
            <Bell size={18} strokeWidth={1.5} />
            {unread > 0 && (
              <span data-testid="notif-badge" className="absolute -top-1.5 -right-1.5 bg-[#4A7C94] text-white text-[10px] leading-none rounded-full min-w-[16px] h-4 flex items-center justify-center px-1">{unread > 9 ? "9+" : unread}</span>
            )}
          </button>
        </div>

        <form onSubmit={doSearch} className="px-3 pt-4">
          <div className="relative">
            <SearchIcon size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#71717A]" />
            <input data-testid="global-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search…"
              className="w-full bg-[#121214] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm pl-9 pr-3 py-2 text-sm transition-colors" />
          </div>
        </form>

        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {visibleNav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} data-testid={`nav-${n.label.toLowerCase().replace(/[\s&]+/g, "-")}`}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 rounded-sm text-sm transition-colors ${
                  isActive ? "bg-[#4A7C94]/15 text-[#4A7C94] border-l-2 border-[#4A7C94]" : "text-[#A1A1AA] hover:bg-[#121214] hover:text-white border-l-2 border-transparent"
                }`
              }>
              <n.icon size={18} strokeWidth={1.5} /> {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-[#27272A] p-4">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-9 w-9 rounded-full bg-[#1A1A1D] border border-[#27272A] flex items-center justify-center overflow-hidden">
              {user?.avatar_url ? <img src={fileUrl(user.avatar_url)} alt="" className="h-full w-full object-cover" /> :
                <span className="text-[#4A7C94] text-sm font-semibold">{(user?.name || "A")[0]}</span>}
            </div>
            <div className="min-w-0">
              <div className="text-sm truncate">{user?.name}</div>
              <div className="text-xs text-[#71717A] truncate">{user?.email}</div>
            </div>
          </div>
          <button data-testid="logout-btn" onClick={doLogout}
            className="w-full flex items-center justify-center gap-2 text-sm text-[#A1A1AA] hover:text-white border border-[#27272A] hover:border-[#4A7C94] rounded-sm py-2.5 transition-colors">
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 ml-64 min-h-screen">
        {isSuper && updateInfo?.update_available && (
          <Link to="/admin" data-testid="update-banner"
            className="flex items-center gap-2 bg-amber-600/90 hover:bg-amber-600 text-white text-sm px-6 py-2.5 transition-colors">
            <AlertTriangle size={16} />
            A new version ({updateInfo.latest_version}) is available. Open the Dashboard to review &amp; apply.
          </Link>
        )}
        <Outlet />
      </main>
    </div>
  );
}
