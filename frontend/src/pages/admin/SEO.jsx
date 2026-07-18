import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Save } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { AdminHeader } from "./AdminHeader";

const inp = "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm transition-colors";

export default function SEO() {
  const [s, setS] = useState(null);
  const [services, setServices] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/settings").then((r) => setS(r.data)).catch(() => {});
    api.get("/services?all=true").then((r) => setServices(r.data)).catch(() => {});
  }, []);

  const save = async () => {
    setBusy(true);
    try {
      await api.put("/settings", {
        seo_title: s.seo_title, seo_description: s.seo_description, seo_keywords: s.seo_keywords,
      });
      toast.success("Global SEO saved");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  if (!s) return null;

  return (
    <div>
      <AdminHeader title="SEO Controls" subtitle="Search engine optimization for the whole site">
        <button data-testid="save-seo" onClick={save} disabled={busy}
          className="bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-60 text-white px-4 py-2 rounded-sm text-sm font-medium flex items-center gap-2 transition-colors">
          <Save size={16} /> Save
        </button>
      </AdminHeader>

      <div className="p-8 max-w-3xl space-y-8">
        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-5">
          <div className="label-caps">Global / Homepage Meta</div>
          <div><label className="label-caps block mb-2">Meta Title</label>
            <input data-testid="seo-title" value={s.seo_title || ""} onChange={(e) => setS({ ...s, seo_title: e.target.value })} className={inp} />
            <p className="text-xs text-[#71717A] mt-1">{(s.seo_title || "").length}/60 chars</p>
          </div>
          <div><label className="label-caps block mb-2">Meta Description</label>
            <textarea data-testid="seo-desc" rows={3} value={s.seo_description || ""} onChange={(e) => setS({ ...s, seo_description: e.target.value })} className={inp} />
            <p className="text-xs text-[#71717A] mt-1">{(s.seo_description || "").length}/160 chars</p>
          </div>
          <div><label className="label-caps block mb-2">Keywords</label>
            <input value={s.seo_keywords || ""} onChange={(e) => setS({ ...s, seo_keywords: e.target.value })} className={inp} />
          </div>
        </div>

        {/* Google preview */}
        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6">
          <div className="label-caps mb-4">Search Preview</div>
          <div className="bg-white rounded-sm p-4">
            <div className="text-[#1a0dab] text-lg leading-tight">{s.seo_title || "Executive Distribution"}</div>
            <div className="text-[#006621] text-sm">executivedistribution.com</div>
            <div className="text-[#545454] text-sm mt-1">{s.seo_description}</div>
          </div>
        </div>

        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6">
          <div className="label-caps mb-4">Per-Service SEO</div>
          <p className="text-sm text-[#71717A] mb-4">Each service page has its own meta fields — edit them from the Services section.</p>
          <div className="space-y-2">
            {services.map((sv) => (
              <div key={sv.id} className="flex items-center justify-between text-sm border-b border-[#27272A]/60 py-2">
                <span>{sv.title}</span>
                <span className={sv.meta_title ? "text-emerald-400 text-xs" : "text-[#71717A] text-xs"}>{sv.meta_title ? "Optimized" : "Default"}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
