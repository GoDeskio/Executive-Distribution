import { NavLink, useNavigate, Outlet } from "react-router-dom";
import {
  LayoutDashboard, Package, Users, HardDrive, Search, Settings as SettingsIcon,
  User, LogOut, Ship,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { fileUrl } from "@/lib/api";
import { useEffect, useState } from "react";
import api from "@/lib/api";

const NAV = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/admin/services", label: "Services", icon: Package },
  { to: "/admin/crm", label: "CRM", icon: Users },
  { to: "/admin/storage", label: "Object Storage", icon: HardDrive },
  { to: "/admin/seo", label: "SEO Controls", icon: Search },
  { to: "/admin/settings", label: "Settings", icon: SettingsIcon },
  { to: "/admin/profile", label: "Profile", icon: User },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [company, setCompany] = useState("Executive Distribution");
  const [logo, setLogo] = useState("");

  useEffect(() => {
    api.get("/settings").then((r) => {
      if (r.data.company_name) setCompany(r.data.company_name);
      if (r.data.logo_url) setLogo(r.data.logo_url);
    }).catch(() => {});
  }, []);

  const doLogout = () => { logout(); navigate("/login"); };

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
          <span className="font-display text-sm leading-tight">{company}</span>
        </div>

        <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} data-testid={`nav-${n.label.toLowerCase().replace(/\s/g, "-")}`}
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
        <Outlet />
      </main>
    </div>
  );
}
