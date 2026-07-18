import { useEffect, useState } from "react";
import { toast } from "sonner";
import { RefreshCw, GitBranch, Save, DownloadCloud, CheckCircle2, AlertTriangle, ShieldCheck } from "lucide-react";
import api, { formatApiError } from "@/lib/api";

const inp = "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm transition-colors";

export function SoftwareUpdates() {
  const [cfg, setCfg] = useState(null);
  const [token, setToken] = useState("");
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState("");

  const loadStatus = () => api.get("/updates/status").then((r) => setStatus(r.data)).catch(() => {});
  const loadCfg = () => api.get("/settings").then((r) => setCfg(r.data)).catch(() => {});

  useEffect(() => { loadCfg(); loadStatus(); }, []);

  const save = async () => {
    setBusy("save");
    try {
      const payload = {
        update_repo_url: cfg.update_repo_url || "",
        update_branch: cfg.update_branch || "main",
        update_auto_check: !!cfg.update_auto_check,
        update_auto_apply: !!cfg.update_auto_apply,
      };
      if (token) payload.update_token = token;
      await api.put("/settings", payload);
      setToken("");
      toast.success("Update settings saved");
      await loadCfg();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(""); }
  };

  const check = async () => {
    setBusy("check");
    try {
      const { data } = await api.post("/updates/check");
      if (data.error) toast.error(`Check failed — ${data.error}`);
      else if (data.update_available) toast.success(`Update available: ${data.update_latest_version || data.latest_version}`);
      else toast.success("You're on the latest version");
      await loadStatus();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(""); }
  };

  const markCurrent = async () => {
    setBusy("mark");
    try {
      const { data } = await api.post("/updates/mark-current");
      if (data.ok) { toast.success(`Baseline set to ${data.current_version}`); await loadStatus(); }
      else toast.error(data.error || "Nothing to mark");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(""); }
  };

  const apply = async () => {
    if (!window.confirm("Apply the latest update now? Services may briefly restart. Your data (users, clients, quotes, documents, settings, uploads) is stored separately and will NOT be affected.")) return;
    setBusy("apply");
    try {
      const { data } = await api.post("/updates/apply");
      toast[data.ok ? "success" : "message"](data.message || (data.ok ? "Update started" : "Not available here"));
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(""); }
  };

  if (!cfg || !status) return null;
  const available = status.update_available;

  return (
    <div data-testid="software-updates" className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 label-caps"><GitBranch size={14} /> Software Updates</div>
        {status.configured && (
          <span data-testid="update-badge" className={`px-2.5 py-1 rounded-sm text-xs flex items-center gap-1 ${available ? "text-amber-300 bg-amber-950/40" : "text-emerald-300 bg-emerald-950/40"}`}>
            {available ? <><AlertTriangle size={12} /> Update available</> : <><CheckCircle2 size={12} /> Up to date</>}
          </span>
        )}
      </div>

      <p className="text-xs text-[#71717A] flex items-start gap-2">
        <ShieldCheck size={14} className="text-emerald-400 mt-0.5 shrink-0" />
        Updates pull application code only. All user, admin & site data (MongoDB) and uploaded files persist through every update.
      </p>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="md:col-span-2">
          <label className="label-caps block mb-2">GitHub Repository URL</label>
          <input data-testid="update-repo-url" value={cfg.update_repo_url || ""} onChange={(e) => setCfg({ ...cfg, update_repo_url: e.target.value })}
            className={inp} placeholder="https://github.com/owner/repo.git" />
        </div>
        <div>
          <label className="label-caps block mb-2">Branch</label>
          <input data-testid="update-branch" value={cfg.update_branch || "main"} onChange={(e) => setCfg({ ...cfg, update_branch: e.target.value })} className={inp} placeholder="main" />
        </div>
        <div>
          <label className="label-caps block mb-2">Access Token {cfg.has_update_token && <span className="text-emerald-400 normal-case">(on file)</span>}</label>
          <input data-testid="update-token" type="password" value={token} onChange={(e) => setToken(e.target.value)} className={inp}
            placeholder={cfg.has_update_token ? "•••••• (leave blank to keep)" : "for private repos (optional)"} />
        </div>
      </div>

      <div className="flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" data-testid="update-auto-check" checked={!!cfg.update_auto_check} onChange={(e) => setCfg({ ...cfg, update_auto_check: e.target.checked })} className="accent-[#4A7C94]" />
          Automatically check for new versions
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" data-testid="update-auto-apply" checked={!!cfg.update_auto_apply} onChange={(e) => setCfg({ ...cfg, update_auto_apply: e.target.checked })} className="accent-[#4A7C94]" />
          Auto-apply <span className="text-[#71717A]">(self-hosted only — needs update script)</span>
        </label>
      </div>

      {status.configured && (
        <div className="text-sm bg-[#0A0A0B] border border-[#27272A] rounded-sm p-4 space-y-1">
          <div className="flex justify-between"><span className="text-[#71717A]">Deployed version</span><span className="font-mono">{status.current_version || "not set"}</span></div>
          <div className="flex justify-between"><span className="text-[#71717A]">Latest {status.latest_kind || "version"}</span>
            <span className="font-mono">{status.latest_version ? (status.latest_url ? <a className="text-[#4A7C94] hover:underline" href={status.latest_url} target="_blank" rel="noreferrer">{status.latest_version}</a> : status.latest_version) : "—"}</span></div>
          {status.last_checked && <div className="flex justify-between"><span className="text-[#71717A]">Last checked</span><span>{new Date(status.last_checked).toLocaleString()}</span></div>}
          {status.last_error && <div className="text-amber-400 text-xs pt-1">{status.last_error}</div>}
          {status.latest_notes && <div className="text-xs text-[#A1A1AA] pt-2 border-t border-[#27272A] mt-2 whitespace-pre-line max-h-24 overflow-auto">{status.latest_notes}</div>}
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <button data-testid="update-save" onClick={save} disabled={busy === "save"}
          className="bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-60 text-white px-4 py-2 rounded-sm text-sm flex items-center gap-2 transition-colors">
          <Save size={15} /> Save
        </button>
        <button data-testid="update-check" onClick={check} disabled={busy === "check"}
          className="border border-[#27272A] hover:border-[#4A7C94] text-[#A1A1AA] hover:text-white px-4 py-2 rounded-sm text-sm flex items-center gap-2 transition-colors">
          <RefreshCw size={15} className={busy === "check" ? "animate-spin" : ""} /> Check now
        </button>
        {available && (
          <>
            <button data-testid="update-apply" onClick={apply} disabled={busy === "apply"}
              className="bg-amber-600 hover:bg-amber-500 disabled:opacity-60 text-white px-4 py-2 rounded-sm text-sm flex items-center gap-2 transition-colors">
              <DownloadCloud size={15} /> Apply update
            </button>
            <button data-testid="update-mark-current" onClick={markCurrent} disabled={busy === "mark"}
              className="border border-[#27272A] hover:border-[#4A7C94] text-[#71717A] hover:text-white px-4 py-2 rounded-sm text-sm transition-colors">
              Mark as current
            </button>
          </>
        )}
      </div>
    </div>
  );
}
