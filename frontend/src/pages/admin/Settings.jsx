import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Save, Upload } from "lucide-react";
import api, { fileUrl, formatApiError } from "@/lib/api";
import { AdminHeader } from "./AdminHeader";

const inp = "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm transition-colors";

export default function Settings() {
  const [s, setS] = useState(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => { api.get("/settings").then((r) => setS(r.data)).catch(() => {}); }, []);

  const save = async () => {
    setBusy(true);
    try { const { seo_title, seo_description, seo_keywords, ...rest } = s; await api.put("/settings", rest); toast.success("Settings saved"); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const uploadLogo = async (file) => {
    setUploading(true);
    const fd = new FormData(); fd.append("file", file); fd.append("category", "asset");
    try { const { data } = await api.post("/files/upload", fd); setS((p) => ({ ...p, logo_url: data.url })); toast.success("Logo uploaded — remember to save"); }
    catch (e) { toast.error("Upload failed"); } finally { setUploading(false); }
  };

  if (!s) return null;
  const F = ({ l, k, area }) => (
    <div><label className="label-caps block mb-2">{l}</label>
      {area ? <textarea rows={3} value={s[k] || ""} onChange={(e) => setS({ ...s, [k]: e.target.value })} className={inp} />
        : <input value={s[k] || ""} onChange={(e) => setS({ ...s, [k]: e.target.value })} className={inp} />}
    </div>
  );

  return (
    <div>
      <AdminHeader title="Settings" subtitle="Site content, branding & contact">
        <button data-testid="save-settings" onClick={save} disabled={busy}
          className="bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-60 text-white px-4 py-2 rounded-sm text-sm font-medium flex items-center gap-2 transition-colors">
          <Save size={16} /> Save
        </button>
      </AdminHeader>

      <div className="p-8 max-w-3xl space-y-6">
        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-5">
          <div className="label-caps">Branding</div>
          <div>
            <label className="label-caps block mb-2">Logo</label>
            <div className="flex items-center gap-4">
              <div className="h-16 w-32 bg-[#0A0A0B] border border-[#27272A] rounded-sm flex items-center justify-center overflow-hidden">
                {s.logo_url ? <img src={fileUrl(s.logo_url)} alt="logo" className="max-h-full max-w-full object-contain" /> : <span className="text-xs text-[#71717A]">No logo</span>}
              </div>
              <label className="border border-[#27272A] hover:border-[#4A7C94] rounded-sm px-4 py-2.5 text-sm cursor-pointer flex items-center gap-2 transition-colors">
                <Upload size={15} /> {uploading ? "Uploading…" : "Upload Logo"}
                <input data-testid="logo-upload" type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files[0] && uploadLogo(e.target.files[0])} />
              </label>
              {s.logo_url && <button onClick={() => setS({ ...s, logo_url: "" })} className="text-xs text-[#71717A] hover:text-red-400">Remove</button>}
            </div>
          </div>
          <F l="Company Name" k="company_name" />
          <F l="Tagline" k="tagline" />
        </div>

        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-5">
          <div className="label-caps">Hero Section</div>
          <F l="Hero Title" k="hero_title" area />
          <F l="Hero Subtitle" k="hero_subtitle" area />
          <F l="Hero Image URL" k="hero_image" />
          <F l="Hero Button Text" k="hero_cta" />
        </div>

        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-5">
          <div className="label-caps">About Section</div>
          <F l="About Text" k="about_text" area />
          <F l="About Image URL" k="about_image" />
        </div>

        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-5">
          <div className="label-caps">Contact & Social</div>
          <div className="grid grid-cols-2 gap-4"><F l="Email" k="contact_email" /><F l="Phone" k="phone" /></div>
          <F l="Address" k="address" />
          <div className="grid grid-cols-3 gap-4"><F l="LinkedIn" k="linkedin" /><F l="Twitter" k="twitter" /><F l="Instagram" k="instagram" /></div>
          <F l="Footer Text" k="footer_text" />
        </div>
      </div>
    </div>
  );
}
