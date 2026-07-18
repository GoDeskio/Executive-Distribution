import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import { useTracking } from "@/hooks/useTracking";
import ProtectedRoute from "@/components/ProtectedRoute";

import Home from "@/pages/Home";
import ServiceDetail from "@/pages/ServiceDetail";
import Login from "@/pages/Login";
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
      <Route path="/admin" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="ai" element={<AiAssistant />} />
        <Route path="documents" element={<Documents />} />
        <Route path="search" element={<Search />} />
        <Route path="services" element={<ServicesAdmin />} />
        <Route path="crm" element={<CRM />} />
        <Route path="storage" element={<Storage />} />
        <Route path="seo" element={<SEO />} />
        <Route path="settings" element={<Settings />} />
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
