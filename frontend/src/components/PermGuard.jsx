import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

const ORDER = [
  ["dashboard", "/admin"], ["ai", "/admin/ai"], ["documents", "/admin/documents"],
  ["services", "/admin/services"], ["crm", "/admin/crm"], ["storage", "/admin/storage"],
  ["seo", "/admin/seo"], ["settings", "/admin/settings"],
];

export function firstAllowedPath(user) {
  if (!user) return "/login";
  if (user.role === "superadmin") return "/admin";
  const perms = user.permissions || [];
  const hit = ORDER.find(([p]) => perms.includes(p));
  return hit ? hit[1] : "/admin/profile";
}

export function PermGuard({ perm, superOnly, children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  const allowed = user.role === "superadmin"
    ? !superOnly || true
    : (superOnly ? false : (user.permissions || []).includes(perm));
  if (!allowed) return <Navigate to={firstAllowedPath(user)} replace />;
  return children;
}
