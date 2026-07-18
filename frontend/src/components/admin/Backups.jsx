import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Database, Download, Save, UploadCloud, Trash2, HardDriveDownload, ShieldCheck } from "lucide-react";
import api, { API, formatApiError } from "@/lib/api";

const inp = "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm transition-colors";

function authedDownload(path, filename) {
  const token = localStorage.getItem("ed_token");
  return fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token}` } })
    .then((r) => { if (!r.ok) throw new Error("download failed"); return r.blob(); })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename; a.click();
      URL.revokeObjectURL(url);
    });
}

export function Backups() {
  const [cfg, setCfg] = useState(null);
  const [busy, setBusy] = useState("");
  const fileRef = useRef(null);

  const load = () => api.get("/backup/config").then((r) => setCfg(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const saveConfig = async () => {
    setBusy("cfg");
    try {
      await api.put("/settings", {
        backup_dir: cfg.backup_dir || "",
        backup_include_files: !!cfg.backup_include_files,
        backup_auto_before_update: !!cfg.backup_auto_before_update,
      });
      toast.success("Backup settings saved");
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(""); }
  };

  const download = async () => {
    setBusy("dl");
    try {
      await authedDownload(`/backup/download?include_files=${!!cfg.backup_include_files}`, "exd-backup.zip");
      toast.success("Backup downloaded");
    } catch { toast.error("Download failed"); }
    finally { setBusy(""); }
  };

  const saveToServer = async () => {
    setBusy("srv");
    try {
      const { data } = await api.post("/backup/save");
      toast.success(`Saved ${data.filename} (${(data.size / 1e6).toFixed(1)} MB)`);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(""); }
  };

  const delServer = async (filename) => {
    if (!window.confirm(`Delete backup ${filename}?`)) return;
    try { await api.delete(`/backup/server/${filename}`); toast.success("Deleted"); await load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const restore = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!window.confirm("⚠️ RESTORE will REPLACE current data (clients, quotes, documents, users, settings) with the contents of this backup. This cannot be undone. Continue?")) return;
    setBusy("restore");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/backup/restore", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Restore complete — reloading…");
      setTimeout(() => window.location.reload(), 1200);
      console.log("restored", data.restored);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail) || "Restore failed"); }
    finally { setBusy(""); }
  };

  if (!cfg) return null;

  return (
    <div data-testid="backups-panel" className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-5">
      <div className="flex items-center gap-2 label-caps"><Database size={14} /> Backups</div>
      <p className="text-xs text-[#71717A] flex items-start gap-2">
        <ShieldCheck size={14} className="text-emerald-400 mt-0.5 shrink-0" />
        Backups capture all data (users, clients, quotes, documents, settings, audit log){cfg.backup_include_files ? " plus uploaded files (logos, images, PDFs)" : ""}. Updates never alter your data — this is your extra safety net.
      </p>

      {/* Destination config */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="md:col-span-2">
          <label className="label-caps block mb-2">Server backup folder</label>
          <input data-testid="backup-dir" value={cfg.backup_dir || ""} onChange={(e) => setCfg({ ...cfg, backup_dir: e.target.value })}
            className={inp} placeholder={cfg.effective_dir} />
          <p className="text-xs text-[#71717A] mt-1">Leave blank to use the default: <span className="font-mono">{cfg.effective_dir}</span>. Use a path on a persistent/mounted volume for self-hosting.</p>
        </div>
      </div>
      <div className="flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" data-testid="backup-include-files" checked={!!cfg.backup_include_files} onChange={(e) => setCfg({ ...cfg, backup_include_files: e.target.checked })} className="accent-[#4A7C94]" />
          Include uploaded files
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" data-testid="backup-auto" checked={!!cfg.backup_auto_before_update} onChange={(e) => setCfg({ ...cfg, backup_auto_before_update: e.target.checked })} className="accent-[#4A7C94]" />
          Auto-backup right before applying an update
        </label>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        <button data-testid="backup-save-config" onClick={saveConfig} disabled={busy === "cfg"}
          className="bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-60 text-white px-4 py-2 rounded-sm text-sm flex items-center gap-2 transition-colors">
          <Save size={15} /> Save settings
        </button>
        <button data-testid="backup-download" onClick={download} disabled={busy === "dl"}
          className="border border-[#27272A] hover:border-[#4A7C94] text-[#A1A1AA] hover:text-white px-4 py-2 rounded-sm text-sm flex items-center gap-2 transition-colors">
          <Download size={15} /> Download to my computer
        </button>
        <button data-testid="backup-save-server" onClick={saveToServer} disabled={busy === "srv"}
          className="border border-[#27272A] hover:border-[#4A7C94] text-[#A1A1AA] hover:text-white px-4 py-2 rounded-sm text-sm flex items-center gap-2 transition-colors">
          <HardDriveDownload size={15} /> {busy === "srv" ? "Saving…" : "Save to server folder"}
        </button>
        <button data-testid="backup-restore-btn" onClick={() => fileRef.current?.click()} disabled={busy === "restore"}
          className="border border-amber-600/60 text-amber-300 hover:bg-amber-950/30 px-4 py-2 rounded-sm text-sm flex items-center gap-2 transition-colors">
          <UploadCloud size={15} /> {busy === "restore" ? "Restoring…" : "Restore from backup"}
        </button>
        <input ref={fileRef} type="file" accept=".zip" onChange={restore} className="hidden" data-testid="backup-restore-input" />
      </div>

      {/* Server backups list */}
      <div>
        <div className="label-caps mb-3">Server Backups ({cfg.server_backups?.length || 0})</div>
        {(!cfg.server_backups || cfg.server_backups.length === 0) ? (
          <p className="text-sm text-[#71717A]">No server backups yet. Use "Save to server folder" to create one.</p>
        ) : (
          <div className="space-y-2" data-testid="server-backups">
            {cfg.server_backups.map((b) => (
              <div key={b.filename} className="flex items-center justify-between border border-[#27272A] rounded-sm px-3 py-2 text-sm">
                <div className="min-w-0">
                  <div className="font-mono truncate">{b.filename}</div>
                  <div className="text-xs text-[#71717A]">{(b.size / 1e6).toFixed(1)} MB · {new Date(b.modified).toLocaleString()}</div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button onClick={() => authedDownload(`/backup/server/${b.filename}`, b.filename)} className="text-[#4A7C94] hover:text-white p-1" title="Download"><Download size={15} /></button>
                  <button onClick={() => delServer(b.filename)} className="text-[#71717A] hover:text-red-400 p-1" title="Delete"><Trash2 size={15} /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
