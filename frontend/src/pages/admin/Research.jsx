import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Globe, Search, Trash2, Loader2, Mail, Phone, Link2, FileSearch, ChevronDown, ChevronRight, ExternalLink, Sparkles, UserPlus } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { AdminHeader } from "./AdminHeader";
import { useAuth } from "@/context/AuthContext";

const inp = "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm transition-colors";

function ResultCard({ r }) {
  const [showText, setShowText] = useState(false);
  const [showLinks, setShowLinks] = useState(false);
  const ok = r.status === "ok";
  return (
    <div data-testid="research-result" className="bg-[#0A0A0B] border border-[#27272A] rounded-sm p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-medium truncate">{r.title || r.url}</div>
          <a href={r.url} target="_blank" rel="noreferrer" className="text-xs text-[#4A7C94] hover:underline flex items-center gap-1 truncate">
            <ExternalLink size={11} /> {r.url}
          </a>
        </div>
        <span className={`shrink-0 px-2 py-0.5 rounded-sm text-xs ${ok ? "text-emerald-300 bg-emerald-950/40" : "text-amber-300 bg-amber-950/40"}`}>
          {ok ? `${r.engine}` : r.status}
        </span>
      </div>
      {!ok && <p className="text-sm text-amber-400">{r.error}</p>}
      {ok && (
        <>
          {r.meta_description && <p className="text-sm text-[#A1A1AA]">{r.meta_description}</p>}
          {r.keyword_matches?.length > 0 && (
            <div className="space-y-2">
              {r.keyword_matches.map((m, i) => (
                <div key={i} className="text-sm">
                  <span className={`font-medium ${m.count ? "text-[#4A7C94]" : "text-[#71717A]"}`}>“{m.keyword}” — {m.count} match{m.count === 1 ? "" : "es"}</span>
                  {m.snippets?.map((s, j) => (
                    <div key={j} className="text-xs text-[#A1A1AA] pl-3 border-l border-[#27272A] mt-1">{s}</div>
                  ))}
                </div>
              ))}
            </div>
          )}
          <div className="flex flex-wrap gap-4 text-xs text-[#71717A]">
            <span>{r.word_count} words</span>
            <span>{r.link_count} links</span>
            <span>{r.emails?.length || 0} emails</span>
            <span>{r.phones?.length || 0} phones</span>
          </div>
          {(r.emails?.length > 0 || r.phones?.length > 0) && (
            <div className="flex flex-wrap gap-2 text-xs">
              {r.emails?.map((e) => <span key={e} className="inline-flex items-center gap-1 bg-[#1A1A1D] px-2 py-1 rounded-sm"><Mail size={11} /> {e}</span>)}
              {r.phones?.map((p) => <span key={p} className="inline-flex items-center gap-1 bg-[#1A1A1D] px-2 py-1 rounded-sm"><Phone size={11} /> {p}</span>)}
            </div>
          )}
          {r.link_count > 0 && (
            <div>
              <button onClick={() => setShowLinks(!showLinks)} className="text-xs text-[#4A7C94] flex items-center gap-1">
                {showLinks ? <ChevronDown size={12} /> : <ChevronRight size={12} />} <Link2 size={12} /> {r.link_count} links
              </button>
              {showLinks && (
                <div className="mt-2 max-h-48 overflow-auto space-y-1">
                  {r.links.map((l, i) => (
                    <a key={i} href={l.url} target="_blank" rel="noreferrer" className="block text-xs text-[#A1A1AA] hover:text-[#4A7C94] truncate">{l.text || l.url}</a>
                  ))}
                </div>
              )}
            </div>
          )}
          {r.text_excerpt && (
            <div>
              <button onClick={() => setShowText(!showText)} className="text-xs text-[#4A7C94] flex items-center gap-1">
                {showText ? <ChevronDown size={12} /> : <ChevronRight size={12} />} <FileSearch size={12} /> Page text
              </button>
              {showText && <p className="mt-2 text-xs text-[#A1A1AA] max-h-48 overflow-auto whitespace-pre-line">{r.text_excerpt}</p>}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function Research() {
  const [keywords, setKeywords] = useState("");
  const [urls, setUrls] = useState("");
  const [render, setRender] = useState(false);
  const [respectRobots, setRespectRobots] = useState(true);
  const [autoImport, setAutoImport] = useState(false);
  const [importTag, setImportTag] = useState("");
  const [pickerTag, setPickerTag] = useState("");
  const [running, setRunning] = useState(false);
  const [current, setCurrent] = useState(null);
  const [history, setHistory] = useState([]);
  const [hasKey, setHasKey] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [savingCrm, setSavingCrm] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [selected, setSelected] = useState({});

  const loadHistory = () => api.get("/research").then((r) => setHistory(r.data)).catch(() => {});
  useEffect(() => {
    loadHistory();
    api.get("/settings").then((r) => setHasKey(!!r.data.has_scraperapi_key)).catch(() => {});
  }, []);

  const run = async () => {
    const urlList = urls.split("\n").map((u) => u.trim()).filter(Boolean);
    if (urlList.length === 0) { toast.error("Add at least one URL (one per line)"); return; }
    setRunning(true);
    try {
      const { data } = await api.post("/research/scrape", {
        keywords, urls: urlList, render, respect_robots: respectRobots,
        auto_import: autoImport, import_tag: importTag,
      });
      setCurrent(data);
      let msg = `Scraped ${data.ok_count}/${data.urls.length} · ${data.total_matches} keyword matches`;
      const s = data.import_summary;
      if (s && (s.created || s.updated)) msg += ` · CRM: ${s.created} new${s.updated ? `, ${s.updated} updated` : ""}`;
      toast.success(msg);
      loadHistory();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setRunning(false); }
  };

  const del = async (id) => {
    try { await api.delete(`/research/${id}`); if (current?.id === id) setCurrent(null); loadHistory(); toast.success("Deleted"); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const summarize = async () => {
    if (!current?.id) return;
    setSummarizing(true);
    try {
      const { data } = await api.post(`/research/${current.id}/summarize`);
      setCurrent({ ...current, ai_summary: data.ai_summary });
      loadHistory();
      toast.success("AI brief ready");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSummarizing(false); }
  };

  const emailContacts = (() => {
    const map = {};
    (current?.results || []).forEach((r) => {
      if (r.status !== "ok") return;
      const phone = (r.phones || [])[0] || "";
      (r.emails || []).forEach((em) => {
        const key = em.toLowerCase();
        if (!map[key]) map[key] = { email: key, title: r.title || "", url: r.url || "", phone };
      });
    });
    return Object.values(map);
  })();
  const emailCount = emailContacts.length;

  const openPicker = () => {
    const all = {};
    emailContacts.forEach((c) => { all[c.email] = true; });
    setSelected(all);
    setPickerOpen(true);
  };

  const selectedCount = Object.values(selected).filter(Boolean).length;

  const saveToCrm = async () => {
    if (!current?.id) return;
    const emails = Object.keys(selected).filter((e) => selected[e]);
    if (emails.length === 0) { toast.error("Select at least one contact"); return; }
    setSavingCrm(true);
    try {
      const tags = pickerTag.trim() ? [pickerTag.trim()] : [];
      const { data } = await api.post(`/research/${current.id}/save-contacts`, { emails, tags });
      const parts = [];
      if (data.created) parts.push(`${data.created} new lead${data.created === 1 ? "" : "s"}`);
      if (data.updated) parts.push(`${data.updated} updated`);
      if (parts.length) toast.success(`CRM: ${parts.join(" · ")}`);
      else toast.info("No changes — contacts already up to date in CRM");
      setPickerOpen(false);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSavingCrm(false); }
  };

  return (
    <div>
      <AdminHeader title="Research" subtitle="Scrape websites for keywords, contacts & links" />
      <div className="p-8 grid lg:grid-cols-3 gap-8">
        {/* Form + results */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-4">
            <div>
              <label className="label-caps block mb-2">Keywords <span className="text-[#71717A] normal-case">(comma separated)</span></label>
              <input data-testid="research-keywords" value={keywords} onChange={(e) => setKeywords(e.target.value)} className={inp} placeholder="e.g. distributor, wholesale, MOQ, contact" />
            </div>
            <div>
              <label className="label-caps block mb-2">Websites <span className="text-[#71717A] normal-case">(one URL per line, max 15)</span></label>
              <textarea data-testid="research-urls" rows={5} value={urls} onChange={(e) => setUrls(e.target.value)} className={inp + " font-mono text-xs"} placeholder={"https://competitor.com\nhttps://supplier.example.com/products"} />
            </div>
            <div className="flex flex-wrap gap-5">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" data-testid="research-render" checked={render} onChange={(e) => setRender(e.target.checked)} className="accent-[#4A7C94]" />
                Render JavaScript {!hasKey && <span className="text-xs text-amber-400">(needs ScraperAPI key in Settings)</span>}
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" data-testid="research-robots" checked={respectRobots} onChange={(e) => setRespectRobots(e.target.checked)} className="accent-[#4A7C94]" />
                Respect robots.txt
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" data-testid="research-autoimport" checked={autoImport} onChange={(e) => setAutoImport(e.target.checked)} className="accent-[#4A7C94]" />
                Auto-save contacts to CRM
              </label>
            </div>
            {autoImport && (
              <div>
                <label className="label-caps block mb-2">Import tag <span className="text-[#71717A] normal-case">(optional — added to every lead)</span></label>
                <input data-testid="research-import-tag" value={importTag} onChange={(e) => setImportTag(e.target.value)} className={inp} placeholder="e.g. Q3-electronics-campaign" />
              </div>
            )}
            <button data-testid="research-run" onClick={run} disabled={running}
              className="bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-60 text-white px-5 py-2.5 rounded-sm text-sm font-medium flex items-center gap-2 transition-colors">
              {running ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />} {running ? "Scraping…" : "Run research"}
            </button>
          </div>

          {current && (
            <div className="space-y-3" data-testid="research-results">
              <div className="flex items-center justify-between">
                <div className="label-caps">Results · {current.ok_count}/{current.urls.length} ok · {current.total_matches} matches</div>
                <div className="flex items-center gap-2">
                  {emailCount > 0 && (
                    <button data-testid="research-save-crm" onClick={openPicker}
                      className="inline-flex items-center gap-2 border border-[#4A7C94] text-[#8FB4C6] hover:bg-[#4A7C94]/10 disabled:opacity-60 px-3 py-1.5 rounded-sm text-xs transition-colors">
                      <UserPlus size={13} /> Save {emailCount} to CRM
                    </button>
                  )}
                  <button data-testid="research-summarize" onClick={summarize} disabled={summarizing}
                    className="inline-flex items-center gap-2 bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-60 text-white px-3 py-1.5 rounded-sm text-xs transition-colors">
                    {summarizing ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />} {summarizing ? "Analyzing…" : (current.ai_summary ? "Regenerate AI brief" : "AI brief")}
                  </button>
                </div>
              </div>
              {current.ai_summary && (
                <div data-testid="research-ai-summary" className="bg-[#4A7C94]/10 border border-[#4A7C94]/30 rounded-sm p-4">
                  <div className="flex items-center gap-2 label-caps mb-2 text-[#8FB4C6]"><Sparkles size={13} /> AI Sourcing Brief</div>
                  <div className="text-sm text-[#D4D4D8] whitespace-pre-line leading-relaxed">{current.ai_summary}</div>
                </div>
              )}
              {current.results.map((r, i) => <ResultCard key={i} r={r} />)}
            </div>
          )}
        </div>

        {/* History */}
        <div>
          <div className="label-caps mb-3">History</div>
          {history.length === 0 ? (
            <p className="text-sm text-[#71717A]">No research runs yet.</p>
          ) : (
            <div className="space-y-2" data-testid="research-history">
              {history.map((h) => (
                <div key={h.id} data-testid={`research-history-${h.id}`} className="bg-[#121214] border border-[#27272A] rounded-sm p-3 flex items-start justify-between gap-2">
                  <button onClick={() => setCurrent(h)} className="min-w-0 text-left">
                    <div className="text-sm truncate flex items-center gap-1"><Globe size={12} className="shrink-0 text-[#4A7C94]" /> {h.urls.length} site{h.urls.length === 1 ? "" : "s"} · {h.total_matches} matches</div>
                    <div className="text-xs text-[#71717A] truncate">{h.keywords_raw || "—"}</div>
                    <div className="text-xs text-[#71717A]">{new Date(h.created_at).toLocaleString()}</div>
                  </button>
                  <button data-testid={`research-delete-${h.id}`} onClick={() => del(h.id)} className="text-[#71717A] hover:text-red-400 p-1 shrink-0"><Trash2 size={15} /></button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {pickerOpen && (
        <div data-testid="crm-picker" className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setPickerOpen(false)}>
          <div className="bg-[#121214] border border-[#27272A] rounded-md w-full max-w-lg max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="p-5 border-b border-[#27272A]">
              <div className="flex items-center gap-2 label-caps text-[#8FB4C6]"><UserPlus size={14} /> Save contacts to CRM</div>
              <p className="text-xs text-[#71717A] mt-1">Choose which extracted emails become leads. Existing leads get enriched, not duplicated.</p>
              <div className="flex gap-3 mt-3 text-xs">
                <button data-testid="crm-picker-all" onClick={() => setSelected(Object.fromEntries(emailContacts.map((c) => [c.email, true])))} className="text-[#4A7C94] hover:underline">Select all</button>
                <button data-testid="crm-picker-none" onClick={() => setSelected({})} className="text-[#71717A] hover:underline">Clear</button>
              </div>
            </div>
            <div className="p-3 overflow-auto space-y-1">
              {emailContacts.map((c) => (
                <label key={c.email} data-testid={`crm-picker-item-${c.email}`} className="flex items-start gap-3 p-2 rounded-sm hover:bg-[#1A1A1D] cursor-pointer">
                  <input type="checkbox" className="mt-1 accent-[#4A7C94]" checked={!!selected[c.email]} onChange={(e) => setSelected({ ...selected, [c.email]: e.target.checked })} />
                  <div className="min-w-0">
                    <div className="text-sm truncate flex items-center gap-1.5"><Mail size={12} className="text-[#4A7C94] shrink-0" /> {c.email}</div>
                    <div className="text-xs text-[#71717A] truncate">{c.title || c.url}{c.phone ? ` · ${c.phone}` : ""}</div>
                  </div>
                </label>
              ))}
            </div>
            <div className="p-4 border-t border-[#27272A] flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <span className="text-xs text-[#71717A] shrink-0">Tag</span>
                <input data-testid="crm-picker-tag" value={pickerTag} onChange={(e) => setPickerTag(e.target.value)}
                  className="bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-2 py-1.5 text-xs w-full max-w-[180px]" placeholder="optional tag" />
              </div>
              <div className="flex gap-2 shrink-0">
                <button onClick={() => setPickerOpen(false)} className="text-sm text-[#A1A1AA] hover:text-white px-4 py-2">Cancel</button>
                <button data-testid="crm-picker-save" onClick={saveToCrm} disabled={savingCrm || selectedCount === 0}
                  className="inline-flex items-center gap-2 bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-60 text-white px-4 py-2 rounded-sm text-sm transition-colors">
                  {savingCrm ? <Loader2 size={14} className="animate-spin" /> : <UserPlus size={14} />} {savingCrm ? "Saving…" : `Save ${selectedCount} to CRM`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
