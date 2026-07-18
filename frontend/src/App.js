import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import { useTracking } from "@/hooks/useTracking";
import ProtectedRoute from "@/components/ProtectedRoute";
import { PermGuard } from "@/components/PermGuard";
import Team from "@/pages/admin/Team";

import Home from "@/pages/Home";
import ServiceDetail from "@/pages/ServiceDetail";
import Login from "@/pages/Login";
import Portal from "@/pages/Portal";
import AdminLayout from "@/pages/admin/AdminLayout";
import Dashboard from "@/pages/admin/Dashboard";
import ServicesAdmin from "@/pages/admin/ServicesAdmin";
import CRM from "@/pages/admin/CRM";
import Storage from "@/pages/admin/Storage";
import SEO from "@/pages/admin/SEO";
import Settings from "@/pages/admin/Settings";
import Profile from "@/pages/admin/Profile";
import AiAssistant from "@/pages/admin/AiAssistant";
import Documents from "@/pages/admin/Documents";
import Search from "@/pages/admin/Search";

function Tracked() {
  useTracking();
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/services/:slug" element={<ServiceDetail />} />
      <Route path="/login" element={<Login />} />
      <Route path="/portal/:token" element={<Portal />} />
      <Route path="/admin" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
        <Route index element={<PermGuard perm="dashboard"><Dashboard /></PermGuard>} />
        <Route path="ai" element={<PermGuard perm="ai"><AiAssistant /></PermGuard>} />
        <Route path="documents" element={<PermGuard perm="documents"><Documents /></PermGuard>} />
        <Route path="search" element={<Search />} />
        <Route path="services" element={<PermGuard perm="services"><ServicesAdmin /></PermGuard>} />
        <Route path="crm" element={<PermGuard perm="crm"><CRM /></PermGuard>} />
        <Route path="storage" element={<PermGuard perm="storage"><Storage /></PermGuard>} />
        <Route path="seo" element={<PermGuard perm="seo"><SEO /></PermGuard>} />
        <Route path="team" element={<PermGuard superOnly><Team /></PermGuard>} />
        <Route path="settings" element={<PermGuard perm="settings"><Settings /></PermGuard>} />
        <Route path="profile" element={<Profile />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Tracked />
        </BrowserRouter>
        <Toaster theme="dark" position="top-right" />
      </AuthProvider>
    </div>
  );
}

export default App;
