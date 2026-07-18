import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, X, Upload, GripVertical } from "lucide-react";
import api, { fileUrl, formatApiError } from "@/lib/api";
import { AdminHeader } from "./AdminHeader";
import { ServiceIcon, ICON_OPTIONS } from "@/components/site/ServiceIcon";

const EMPTY = {
  title: "", short_description: "", full_description: "", image_url: "", icon: "package",
  order: 0, published: true, features: [], sections: [], meta_title: "", meta_description: "", keywords: "",
};

export default function ServicesAdmin() {
  const [services, setServices] = useState([]);
  const [editing, setEditing] = useState(null);
  const [uploading, setUploading] = useState(false);

  const load = () => api.get("/services?all=true").then((r) => setServices(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const openNew = () => setEditing({ ...EMPTY, order: services.length });
  const openEdit = (s) => setEditing({ ...EMPTY, ...s, features: s.features || [], sections: s.sections || [] });

  const save = async () => {
    if (!editing.title.trim()) return toast.error("Title is required");
    const payload = { ...editing };
    delete payload.id; delete payload.slug; delete payload.created_at; delete payload.updated_at;
    try {
      if (editing.id) await api.put(`/services/${editing.id}`, payload);
      else await api.post("/services", payload);
      toast.success("Service saved");
      setEditing(null);
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this service?")) return;
    await api.delete(`/services/${id}`);
    toast.success("Service deleted");
    load();
  };

  const uploadImage = async (file) => {
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("category", "asset");
    try {
      const { data } = await api.post("/files/upload", fd);
      setEditing((p) => ({ ...p, image_url: fileUrl(data.url) }));
      toast.success("Image uploaded");
    } catch (e) { toast.error("Upload failed"); }
    finally { setUploading(false); }
  };

  return (
    <div>
      <AdminHeader title="Services" subtitle="Create and manage program pages">
        <button data-testid="new-service-btn" onClick={openNew}
          className="bg-[#4A7C94] hover:bg-[#5A8CA4] transition-colors text-white px-4 py-2 rounded-sm text-sm font-medium flex items-center gap-2">
          <Plus size={16} /> New Service
        </button>
      </AdminHeader>

      <div className="p-8">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {services.map((s) => (
            <div key={s.id} data-testid={`admin-service-${s.slug}`}
              className="bg-[#121214] border border-[#27272A] rounded-md overflow-hidden group">
              <div className="h-32 overflow-hidden relative">
                {s.image_url ? <img src={s.image_url} alt="" className="w-full h-full object-cover" /> :
                  <div className="w-full h-full bg-[#1A1A1D]" />}
                {!s.published && <span className="absolute top-2 right-2 bg-[#0A0A0B]/80 text-[#71717A] text-xs px-2 py-1 rounded-sm">Draft</span>}
              </div>
              <div className="p-5">
                <div className="flex items-center gap-2 mb-2">
                  <ServiceIcon name={s.icon} size={15} className="text-[#4A7C94]" strokeWidth={1.5} />
                  <h3 className="font-medium truncate">{s.title}</h3>
                </div>
                <p className="text-xs text-[#71717A] line-clamp-2 mb-4">{s.short_description}</p>
                <div className="flex gap-2">
                  <button data-testid={`edit-${s.slug}`} onClick={() => openEdit(s)}
                    className="flex-1 border border-[#27272A] hover:border-[#4A7C94] rounded-sm py-2 text-xs flex items-center justify-center gap-1 transition-colors">
                    <Pencil size={13} /> Edit
                  </button>
                  <button data-testid={`delete-${s.slug}`} onClick={() => remove(s.id)}
                    className="border border-[#27272A] hover:border-red-700 hover:text-red-400 rounded-sm py-2 px-3 text-xs transition-colors">
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {editing && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center overflow-y-auto p-6">
          <div className="bg-[#121214] border border-[#27272A] rounded-md w-full max-w-2xl my-8">
            <div className="flex items-center justify-between p-6 border-b border-[#27272A] sticky top-0 bg-[#121214]">
              <h2 className="font-display text-lg">{editing.id ? "Edit Service" : "New Service"}</h2>
              <button data-testid="close-editor" onClick={() => setEditing(null)} className="text-[#71717A] hover:text-white"><X size={20} /></button>
            </div>

            <div className="p-6 space-y-5">
              <Field label="Title">
                <input data-testid="svc-title" value={editing.title} onChange={(e) => setEditing({ ...editing, title: e.target.value })} className={inp} />
              </Field>

              <div className="grid grid-cols-2 gap-4">
                <Field label="Icon">
                  <select data-testid="svc-icon" value={editing.icon} onChange={(e) => setEditing({ ...editing, icon: e.target.value })} className={inp}>
                    {ICON_OPTIONS.map((i) => <option key={i} value={i}>{i}</option>)}
                  </select>
                </Field>
                <Field label="Order">
                  <input type="number" value={editing.order} onChange={(e) => setEditing({ ...editing, order: +e.target.value })} className={inp} />
                </Field>
              </div>

              <Field label="Image">
                <div className="flex gap-3 items-center">
                  {editing.image_url && <img src={editing.image_url} alt="" className="h-14 w-20 object-cover rounded-sm border border-[#27272A]" />}
                  <input value={editing.image_url} onChange={(e) => setEditing({ ...editing, image_url: e.target.value })} placeholder="Image URL" className={inp} />
                  <label className="shrink-0 border border-[#27272A] hover:border-[#4A7C94] rounded-sm px-3 py-2.5 text-xs cursor-pointer flex items-center gap-1 transition-colors">
                    <Upload size={13} /> {uploading ? "…" : "Upload"}
                    <input data-testid="svc-image-upload" type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files[0] && uploadImage(e.target.files[0])} />
                  </label>
                </div>
              </Field>

              <Field label="Short Description">
                <textarea data-testid="svc-short" rows={2} value={editing.short_description} onChange={(e) => setEditing({ ...editing, short_description: e.target.value })} className={inp} />
              </Field>

              <Field label="Full Description">
                <textarea data-testid="svc-full" rows={5} value={editing.full_description} onChange={(e) => setEditing({ ...editing, full_description: e.target.value })} className={inp} />
              </Field>

              <Field label="Features (one per line)">
                <textarea rows={3} value={editing.features.join("\n")} onChange={(e) => setEditing({ ...editing, features: e.target.value.split("\n").filter(Boolean) })} className={inp} />
              </Field>

              <div className="border-t border-[#27272A] pt-5">
                <div className="label-caps mb-4">SEO</div>
                <div className="space-y-4">
                  <Field label="Meta Title"><input value={editing.meta_title} onChange={(e) => setEditing({ ...editing, meta_title: e.target.value })} className={inp} /></Field>
                  <Field label="Meta Description"><textarea rows={2} value={editing.meta_description} onChange={(e) => setEditing({ ...editing, meta_description: e.target.value })} className={inp} /></Field>
                  <Field label="Keywords"><input value={editing.keywords} onChange={(e) => setEditing({ ...editing, keywords: e.target.value })} className={inp} /></Field>
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={editing.published} onChange={(e) => setEditing({ ...editing, published: e.target.checked })} className="accent-[#4A7C94]" />
                Published (visible on website)
              </label>
            </div>

            <div className="flex gap-3 p-6 border-t border-[#27272A] sticky bottom-0 bg-[#121214]">
              <button onClick={() => setEditing(null)} className="flex-1 border border-[#27272A] hover:bg-[#1A1A1D] rounded-sm py-2.5 text-sm transition-colors">Cancel</button>
              <button data-testid="save-service" onClick={save} className="flex-1 bg-[#4A7C94] hover:bg-[#5A8CA4] rounded-sm py-2.5 text-sm font-medium text-white transition-colors">Save Service</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const inp = "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm transition-colors";
function Field({ label, children }) {
  return <div><label className="label-caps block mb-2">{label}</label>{children}</div>;
}
