import { useState } from "react";
import { toast } from "sonner";
import { Save, Upload } from "lucide-react";
import api, { fileUrl, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { AdminHeader } from "./AdminHeader";

const inp = "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm transition-colors";

export default function Profile() {
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [avatar, setAvatar] = useState(user?.avatar_url || "");
  const [cur, setCur] = useState("");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);

  const saveProfile = async () => {
    setBusy(true);
    try {
      const { data } = await api.put("/auth/profile", { name, avatar_url: avatar });
      setUser(data); toast.success("Profile updated");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const changePassword = async () => {
    if (!pw) return toast.error("Enter a new password");
    try {
      const { data } = await api.put("/auth/profile", { current_password: cur, new_password: pw });
      setUser(data); setCur(""); setPw(""); toast.success("Password changed");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const uploadAvatar = async (file) => {
    setUploading(true);
    const fd = new FormData(); fd.append("file", file); fd.append("category", "asset");
    try { const { data } = await api.post("/files/upload", fd); setAvatar(data.url); toast.success("Avatar uploaded — save to apply"); }
    catch (e) { toast.error("Upload failed"); } finally { setUploading(false); }
  };

  return (
    <div>
      <AdminHeader title="Profile" subtitle="Manage your account" />
      <div className="p-8 max-w-2xl space-y-6">
        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-5">
          <div className="label-caps">Account</div>
          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-full bg-[#0A0A0B] border border-[#27272A] flex items-center justify-center overflow-hidden">
              {avatar ? <img src={fileUrl(avatar)} alt="" className="h-full w-full object-cover" /> : <span className="text-2xl text-[#4A7C94] font-display">{(name || "A")[0]}</span>}
            </div>
            <label className="border border-[#27272A] hover:border-[#4A7C94] rounded-sm px-4 py-2.5 text-sm cursor-pointer flex items-center gap-2 transition-colors">
              <Upload size={15} /> {uploading ? "Uploading…" : "Change Avatar"}
              <input data-testid="avatar-upload" type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files[0] && uploadAvatar(e.target.files[0])} />
            </label>
          </div>
          <div><label className="label-caps block mb-2">Name</label><input data-testid="profile-name" value={name} onChange={(e) => setName(e.target.value)} className={inp} /></div>
          <div><label className="label-caps block mb-2">Email</label><input value={user?.email || ""} disabled className={inp + " opacity-60"} /></div>
          <button data-testid="save-profile" onClick={saveProfile} disabled={busy}
            className="bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-60 text-white px-5 py-2.5 rounded-sm text-sm font-medium flex items-center gap-2 transition-colors">
            <Save size={16} /> Save Profile
          </button>
        </div>

        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-5">
          <div className="label-caps">Change Password</div>
          <div><label className="label-caps block mb-2">Current Password</label><input data-testid="current-password" type="password" value={cur} onChange={(e) => setCur(e.target.value)} className={inp} /></div>
          <div><label className="label-caps block mb-2">New Password</label><input data-testid="new-password" type="password" value={pw} onChange={(e) => setPw(e.target.value)} className={inp} /></div>
          <button data-testid="change-password" onClick={changePassword}
            className="border border-[#27272A] hover:border-[#4A7C94] px-5 py-2.5 rounded-sm text-sm transition-colors">Update Password</button>
        </div>
      </div>
    </div>
  );
}
