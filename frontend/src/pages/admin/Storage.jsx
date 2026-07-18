import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Upload, Trash2, Copy, Image as ImageIcon } from "lucide-react";
import api, { fileUrl } from "@/lib/api";
import { AdminHeader } from "./AdminHeader";

export default function Storage() {
  const [assets, setAssets] = useState([]);
  const [uploading, setUploading] = useState(false);

  const load = () => api.get("/files?category=asset").then((r) => setAssets(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const upload = async (files) => {
    setUploading(true);
    for (const file of files) {
      const fd = new FormData(); fd.append("file", file); fd.append("category", "asset");
      try { await api.post("/files/upload", fd); } catch (e) { toast.error(`Failed: ${file.name}`); }
    }
    setUploading(false); toast.success("Upload complete"); load();
  };

  const remove = async (id) => { if (!window.confirm("Delete asset?")) return; await api.delete(`/files/${id}`); load(); toast.success("Deleted"); };
  const copy = (url) => { navigator.clipboard.writeText(fileUrl(url)); toast.success("URL copied"); };

  const isImage = (ct) => ct?.startsWith("image/");

  return (
    <div>
      <AdminHeader title="Object Storage" subtitle="Assets, logos & media">
        <label className="bg-[#4A7C94] hover:bg-[#5A8CA4] text-white px-4 py-2 rounded-sm text-sm font-medium flex items-center gap-2 cursor-pointer transition-colors">
          <Upload size={16} /> {uploading ? "Uploading…" : "Upload Assets"}
          <input data-testid="asset-upload" type="file" multiple className="hidden" onChange={(e) => e.target.files.length && upload([...e.target.files])} />
        </label>
      </AdminHeader>

      <div className="p-8">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {assets.length === 0 && <p className="text-[#71717A] text-sm col-span-full">No assets uploaded yet. Upload images, logos and media here.</p>}
          {assets.map((a) => (
            <div key={a.id} data-testid={`asset-${a.id}`} className="bg-[#121214] border border-[#27272A] rounded-md overflow-hidden group">
              <div className="h-32 bg-[#0A0A0B] flex items-center justify-center overflow-hidden">
                {isImage(a.content_type)
                  ? <img src={fileUrl(a.url)} alt={a.original_filename} className="w-full h-full object-cover" />
                  : <ImageIcon size={28} className="text-[#71717A]" />}
              </div>
              <div className="p-3">
                <div className="text-xs truncate mb-2">{a.original_filename}</div>
                <div className="flex gap-1">
                  <button data-testid={`copy-${a.id}`} onClick={() => copy(a.url)} className="flex-1 border border-[#27272A] hover:border-[#4A7C94] rounded-sm py-1.5 text-xs flex items-center justify-center gap-1 transition-colors"><Copy size={12} /> Copy URL</button>
                  <button onClick={() => remove(a.id)} className="border border-[#27272A] hover:border-red-700 hover:text-red-400 rounded-sm py-1.5 px-2 transition-colors"><Trash2 size={12} /></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
