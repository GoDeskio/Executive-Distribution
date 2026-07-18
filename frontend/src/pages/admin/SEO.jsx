import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Save, Plus, Trash2, ExternalLink, Rss } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { AdminHeader } from "./AdminHeader";

const inp = "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm transition-colors";

export default function SEO() {
  const [s, setS] = useState(null);
  const [services, setServices] = useState([]);
  const [busy, setBusy] = useState(false);
  const [pinging, setPinging] = useState(false);

  useEffect(() => {
    api.get("/settings").then((r) => setS(r.data)).catch(() => {});
    api.get("/services?all=true").then((r) => setServices(r.data)).catch(() => {});
  }, []);

  const save = async () => {
    setBusy(true);
    try {
      await api.put("/settings", {
        seo_title: s.seo_title, seo_description: s.seo_description, seo_keywords: s.seo_keywords,
        site_url: s.site_url || "", page_seo: s.page_seo || [],
        search_engine_ping_enabled: !!s.search_engine_ping_enabled,
        indexnow_key: s.indexnow_key || "",
      });
      toast.success("SEO settings saved");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const pingNow = async () => {
    setPinging(true);
    try {
      const { data } = await api.post("/seo/ping");
      const parts = Object.entries(data.results || {}).map(([k, v]) => `${k}: ${v}`).join(" · ");
      toast.success(`Search engines notified — ${parts}`);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail) || "Ping failed"); }
    finally { setPinging(false); }
  };

  const pages = s?.page_seo || [];
  const setPages = (next) => setS({ ...s, page_seo: next });
  const addPage = () => setPages([...pages, { path: "", title: "", description: "", keywords: "" }]);
  const updatePage = (i, key, val) => setPages(pages.map((p, idx) => (idx === i ? { ...p, [key]: val } : p)));
  const removePage = (i) => setPages(pages.filter((_, idx) => idx !== i));

  const backend = process.env.REACT_APP_BACKEND_URL;

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

        {/* Sitemap & robots */}
        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-5">
          <div className="label-caps">Sitemap &amp; Robots</div>
          <div>
            <label className="label-caps block mb-2">Canonical Site URL</label>
            <input data-testid="seo-site-url" value={s.site_url || ""} onChange={(e) => setS({ ...s, site_url: e.target.value })} className={inp}
              placeholder="https://www.executivedistribution.com" />
            <p className="text-xs text-[#71717A] mt-1">Used to build absolute URLs in your sitemap. Leave blank to auto-detect from the request host.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <a data-testid="view-sitemap" href={`${backend}/api/sitemap.xml`} target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-2 border border-[#27272A] hover:border-[#4A7C94] rounded-sm px-3 py-2 text-sm transition-colors">
              <ExternalLink size={14} /> View sitemap.xml
            </a>
            <a data-testid="view-robots" href={`${backend}/api/robots.txt`} target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-2 border border-[#27272A] hover:border-[#4A7C94] rounded-sm px-3 py-2 text-sm transition-colors">
              <ExternalLink size={14} /> View robots.txt
            </a>
          </div>
          <p className="text-xs text-[#71717A]">Sitemap regenerates automatically from your published services and per-page overrides below.</p>
        </div>

        {/* Search engine notifications */}
        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-5">
          <div className="flex items-center gap-2 label-caps"><Rss size={14} /> Search Engine Notifications</div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" data-testid="seo-autoping" checked={!!s.search_engine_ping_enabled}
              onChange={(e) => setS({ ...s, search_engine_ping_enabled: e.target.checked })} className="accent-[#4A7C94]" />
            Auto-notify search engines when services or SEO change (requires a canonical Site URL)
          </label>
          <div>
            <label className="label-caps block mb-2">IndexNow Key <span className="text-[#71717A] normal-case">(optional — enables instant Bing/Yandex indexing)</span></label>
            <input data-testid="seo-indexnow-key" value={s.indexnow_key || ""} onChange={(e) => setS({ ...s, indexnow_key: e.target.value })} className={inp}
              placeholder="e.g. a 32-char hex key you generate" />
            <p className="text-xs text-[#71717A] mt-1">The key file is served automatically at <span className="font-mono">/api/indexnow/&lt;key&gt;.txt</span>. Note: Google &amp; Bing have retired the legacy sitemap-ping endpoints; IndexNow is the current standard.</p>
          </div>
          <button data-testid="seo-ping-now" onClick={pingNow} disabled={pinging}
            className="inline-flex items-center gap-2 border border-[#4A7C94]/60 text-[#4A7C94] hover:bg-[#4A7C94]/10 disabled:opacity-60 rounded-sm px-4 py-2 text-sm transition-colors">
            <Rss size={14} /> {pinging ? "Notifying…" : "Ping search engines now"}
          </button>
        </div>

        {/* Per-page SEO overrides */}
        <div className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="label-caps">Per-Page SEO Overrides</div>
            <button data-testid="add-page-seo" onClick={addPage}
              className="inline-flex items-center gap-2 border border-[#4A7C94]/60 text-[#4A7C94] hover:bg-[#4A7C94]/10 rounded-sm px-3 py-1.5 text-sm transition-colors">
              <Plus size={14} /> Add page
            </button>
          </div>
          <p className="text-sm text-[#71717A]">Override meta tags for specific routes (e.g. <span className="font-mono text-[#A1A1AA]">about</span>, <span className="font-mono text-[#A1A1AA]">contact</span>). These paths are also added to the sitemap.</p>
          {pages.length === 0 && <p className="text-sm text-[#71717A] border border-dashed border-[#27272A] rounded-sm py-6 text-center">No overrides yet.</p>}
          <div className="space-y-4">
            {pages.map((p, i) => (
              <div key={i} data-testid={`page-seo-row-${i}`} className="border border-[#27272A] rounded-sm p-4 space-y-3">
                <div className="flex items-center gap-3">
                  <input data-testid={`page-seo-path-${i}`} value={p.path || ""} onChange={(e) => updatePage(i, "path", e.target.value)}
                    className={inp + " font-mono"} placeholder="Path e.g. about" />
                  <button data-testid={`remove-page-seo-${i}`} onClick={() => removePage(i)} className="shrink-0 text-[#71717A] hover:text-red-400 p-2"><Trash2 size={16} /></button>
                </div>
                <input data-testid={`page-seo-title-${i}`} value={p.title || ""} onChange={(e) => updatePage(i, "title", e.target.value)} className={inp} placeholder="Meta title" />
                <textarea data-testid={`page-seo-desc-${i}`} rows={2} value={p.description || ""} onChange={(e) => updatePage(i, "description", e.target.value)} className={inp} placeholder="Meta description" />
                <input data-testid={`page-seo-keywords-${i}`} value={p.keywords || ""} onChange={(e) => updatePage(i, "keywords", e.target.value)} className={inp} placeholder="Keywords (comma separated)" />
              </div>
            ))}
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
