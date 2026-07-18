import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2, X, FileText, Download, FileCheck, FolderDown, Wand2, Sparkles } from "lucide-react";
import api, { fileUrl, formatApiError } from "@/lib/api";
import { AdminHeader } from "./AdminHeader";

const inp = "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm transition-colors";
const emptyLine = { item: "", qty: 1, unit_price: 0, fees: 0, customs: 0, total: 0 };
const EMPTY = {
  doc_type: "quote", client_id: "", client_name: "", client_company: "", client_email: "", client_phone: "",
  destination: "", port: "", po_number: "", tracking_number: "", date: "", line_items: [{ ...emptyLine }],
  tax_total: 0, notes: "",
};

const DTYPE_LABEL = { quote: "Quote", receipt: "Receipt", customs: "Customs Doc" };

export default function Documents() {
  const [tab, setTab] = useState("builder");
  return (
    <div>
      <AdminHeader title="Quotes & Documents" subtitle="Create quotes, receipts & customs docs with your logo watermark" />
      <div className="px-8 pt-6">
        <div className="flex gap-1 border-b border-[#27272A]">
          {[["builder", "Documents", FileText], ["folder", "Send to Client", FolderDown]].map(([k, l, Icon]) => (
            <button key={k} data-testid={`docs-tab-${k}`} onClick={() => setTab(k)}
              className={`flex items-center gap-2 px-5 py-3 text-sm border-b-2 -mb-px transition-colors ${tab === k ? "border-[#4A7C94] text-[#4A7C94]" : "border-transparent text-[#A1A1AA] hover:text-white"}`}>
              <Icon size={15} /> {l}
            </button>
          ))}
        </div>
      </div>
      <div className="p-8">{tab === "builder" ? <Builder /> : <SendToClient />}</div>
    </div>
  );
}

function Builder() {
  const [docs, setDocs] = useState([]);
  const [clients, setClients] = useState([]);
  const [editing, setEditing] = useState(null);
  const [ai, setAi] = useState(null); // { desc, client_id }
  const [aiBusy, setAiBusy] = useState(false);

  const load = () => api.get("/documents").then((r) => setDocs(r.data)).catch(() => {});
  useEffect(() => { load(); api.get("/clients").then((r) => setClients(r.data)).catch(() => {}); }, []);

  const totals = (li, tax) => {
    const items = li.map((l) => ({ ...l, total: (+l.qty || 0) * (+l.unit_price || 0) + (+l.fees || 0) + (+l.customs || 0) }));
    const subtotal = items.reduce((s, l) => s + (+l.qty || 0) * (+l.unit_price || 0), 0);
    const fees_total = items.reduce((s, l) => s + (+l.fees || 0), 0);
    const customs_total = items.reduce((s, l) => s + (+l.customs || 0), 0);
    const tax_total = +tax || 0;
    return { items, subtotal, fees_total, customs_total, tax_total, grand_total: subtotal + fees_total + customs_total + tax_total };
  };

  const save = async () => {
    if (!editing.client_name.trim()) return toast.error("Client name is required");
    const t = totals(editing.line_items, editing.tax_total);
    const payload = { ...editing, line_items: t.items, subtotal: t.subtotal, fees_total: t.fees_total, customs_total: t.customs_total, tax_total: t.tax_total, grand_total: t.grand_total };
    delete payload.id; delete payload.created_at; delete payload.number; delete payload.pdf_file_id;
    try {
      if (editing.id) await api.put(`/documents/${editing.id}`, payload);
      else await api.post("/documents", payload);
      toast.success("Document saved"); setEditing(null); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const remove = async (id) => { if (!window.confirm("Delete document?")) return; await api.delete(`/documents/${id}`); load(); toast.success("Deleted"); };

  const generate = async (id) => {
    toast.loading("Generating PDF…", { id: "gen" });
    try {
      const { data } = await api.post(`/documents/${id}/generate`);
      toast.success("PDF generated & saved to Send to Client", { id: "gen" });
      load();
      window.open(fileUrl(data.url), "_blank");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail) || "Generation failed", { id: "gen" }); }
  };

  const openNew = (type = "quote") => setEditing({ ...EMPTY, doc_type: type, line_items: [{ ...emptyLine }] });
  const pickClient = (id) => {
    const c = clients.find((x) => x.id === id);
    if (c) setEditing((p) => ({ ...p, client_id: c.id, client_name: c.name, client_company: c.company, client_email: c.email, client_phone: c.phone }));
  };

  const runAiDraft = async () => {
    if (!ai.desc.trim()) return toast.error("Describe the shipment first");
    setAiBusy(true);
    const c = clients.find((x) => x.id === ai.client_id);
    try {
      const { data } = await api.post("/documents/ai-draft", {
        description: ai.desc, doc_type: "quote",
        client_id: c?.id || "", client_name: c?.name || "",
      });
      const draft = {
        ...EMPTY, ...data,
        client_name: data.client_name || c?.name || "Prospect",
        client_company: c?.company || "", client_email: c?.email || "", client_phone: c?.phone || "",
        line_items: data.line_items?.length ? data.line_items : [{ ...emptyLine }],
      };
      setAi(null);
      setEditing(draft);
      toast.success("AI draft ready — review and save");
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail) || "AI draft failed");
    } finally { setAiBusy(false); }
  };

  const t = editing ? totals(editing.line_items, editing.tax_total) : null;

  return (
    <div>
      <div className="flex justify-end gap-2 mb-4">
        <button data-testid="ai-draft-btn" onClick={() => setAi({ desc: "", client_id: "" })}
          className="border border-[#4A7C94]/60 text-[#4A7C94] hover:bg-[#4A7C94]/10 px-4 py-2 rounded-sm text-sm font-medium flex items-center gap-2 transition-colors"><Sparkles size={16} /> AI Draft Quote</button>
        <button data-testid="new-quote-btn" onClick={() => openNew("quote")} className="bg-[#4A7C94] hover:bg-[#5A8CA4] text-white px-4 py-2 rounded-sm text-sm font-medium flex items-center gap-2 transition-colors"><Plus size={16} /> New Quote</button>
        <button data-testid="new-receipt-btn" onClick={() => openNew("receipt")} className="border border-[#27272A] hover:border-[#4A7C94] px-4 py-2 rounded-sm text-sm flex items-center gap-2 transition-colors"><Plus size={16} /> Receipt</button>
        <button data-testid="new-customs-btn" onClick={() => openNew("customs")} className="border border-[#27272A] hover:border-[#4A7C94] px-4 py-2 rounded-sm text-sm flex items-center gap-2 transition-colors"><Plus size={16} /> Customs</button>
      </div>

      <div className="bg-[#121214] border border-[#27272A] rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-[#27272A] text-left text-[#71717A] text-xs uppercase tracking-wide">
            <th className="px-6 py-4">Number</th><th className="px-6 py-4">Type</th><th className="px-6 py-4">Client</th>
            <th className="px-6 py-4">Total</th><th className="px-6 py-4">Status</th><th className="px-6 py-4">Date</th><th className="px-6 py-4"></th>
          </tr></thead>
          <tbody>
            {docs.length === 0 && <tr><td colSpan={7} className="px-6 py-10 text-center text-[#71717A]">No documents yet. Create a quote to get started.</td></tr>}
            {docs.map((d) => (
              <tr key={d.id} data-testid={`doc-row-${d.id}`} className="border-b border-[#27272A]/60 hover:bg-[#1A1A1D]/40">
                <td className="px-6 py-4 font-mono text-xs">{d.number}</td>
                <td className="px-6 py-4">{DTYPE_LABEL[d.doc_type] || d.doc_type}</td>
                <td className="px-6 py-4">{d.client_name}</td>
                <td className="px-6 py-4">${(d.grand_total || 0).toLocaleString()}</td>
                <td className="px-6 py-4"><span className={`text-xs px-2 py-1 rounded-sm ${d.status === "generated" ? "text-emerald-300 bg-emerald-950/40" : "text-[#A1A1AA] bg-[#1A1A1D]"}`}>{d.status}</span></td>
                <td className="px-6 py-4 text-[#71717A] text-xs">{d.date}</td>
                <td className="px-6 py-4 text-right whitespace-nowrap">
                  <button data-testid={`generate-${d.id}`} onClick={() => generate(d.id)} title="Generate PDF" className="text-[#4A7C94] hover:text-white p-1 mr-1"><Wand2 size={15} /></button>
                  <button onClick={() => setEditing({ ...EMPTY, ...d, line_items: d.line_items?.length ? d.line_items : [{ ...emptyLine }] })} title="Edit" className="text-[#71717A] hover:text-white p-1 mr-1"><FileCheck size={15} /></button>
                  <button onClick={() => remove(d.id)} className="text-[#71717A] hover:text-red-400 p-1"><Trash2 size={15} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {ai && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center overflow-y-auto p-6">
          <div className="bg-[#121214] border border-[#27272A] rounded-md w-full max-w-lg my-8">
            <div className="flex items-center justify-between p-6 border-b border-[#27272A]">
              <h2 className="font-display text-lg flex items-center gap-2"><Sparkles size={18} className="text-[#4A7C94]" /> AI Draft Quote</h2>
              <button data-testid="close-ai-draft" onClick={() => setAi(null)} className="text-[#71717A] hover:text-white"><X size={20} /></button>
            </div>
            <div className="p-6 space-y-4">
              <F l="Link Client (optional)">
                <select data-testid="ai-draft-client" value={ai.client_id} onChange={(e) => setAi({ ...ai, client_id: e.target.value })} className={inp}>
                  <option value="">— none —</option>
                  {clients.map((c) => <option key={c.id} value={c.id}>{c.name}{c.company ? ` (${c.company})` : ""}</option>)}
                </select>
              </F>
              <F l="Describe the shipment">
                <textarea data-testid="ai-draft-desc" rows={5} value={ai.desc} onChange={(e) => setAi({ ...ai, desc: e.target.value })} className={inp}
                  placeholder="e.g. 300 boxes of premium cigars (~900kg, $60,000) ocean freight from Santo Domingo to Port of Miami, plus 50kg of Larimar worth $12,000." />
              </F>
              <p className="text-xs text-[#71717A]">The AI extracts line items and the required documents; fees, customs and taxes are then computed from your Fee Calculator rules. You can edit everything before saving.</p>
            </div>
            <div className="flex gap-3 p-6 border-t border-[#27272A]">
              <button onClick={() => setAi(null)} className="flex-1 border border-[#27272A] hover:bg-[#1A1A1D] rounded-sm py-2.5 text-sm transition-colors">Cancel</button>
              <button data-testid="run-ai-draft" onClick={runAiDraft} disabled={aiBusy}
                className="flex-1 bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-60 rounded-sm py-2.5 text-sm font-medium text-white transition-colors flex items-center justify-center gap-2">
                {aiBusy ? "Drafting…" : <>Generate Draft <Sparkles size={15} /></>}
              </button>
            </div>
          </div>
        </div>
      )}

      {editing && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center overflow-y-auto p-6">
          <div className="bg-[#121214] border border-[#27272A] rounded-md w-full max-w-3xl my-8">
            <div className="flex items-center justify-between p-6 border-b border-[#27272A] sticky top-0 bg-[#121214] z-10">
              <h2 className="font-display text-lg">{editing.id ? `Edit ${DTYPE_LABEL[editing.doc_type]}` : `New ${DTYPE_LABEL[editing.doc_type]}`}</h2>
              <button data-testid="close-doc" onClick={() => setEditing(null)} className="text-[#71717A] hover:text-white"><X size={20} /></button>
            </div>
            <div className="p-6 space-y-5">
              <div>
                <label className="label-caps block mb-2">Link Client (optional)</label>
                <select data-testid="doc-client" value={editing.client_id} onChange={(e) => pickClient(e.target.value)} className={inp}>
                  <option value="">— Select client to autofill —</option>
                  {clients.map((c) => <option key={c.id} value={c.id}>{c.name}{c.company ? ` (${c.company})` : ""}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <F l="Client Name *"><input data-testid="doc-client-name" value={editing.client_name} onChange={(e) => setEditing({ ...editing, client_name: e.target.value })} className={inp} /></F>
                <F l="Company"><input value={editing.client_company} onChange={(e) => setEditing({ ...editing, client_company: e.target.value })} className={inp} /></F>
                <F l="Email"><input value={editing.client_email} onChange={(e) => setEditing({ ...editing, client_email: e.target.value })} className={inp} /></F>
                <F l="Phone"><input value={editing.client_phone} onChange={(e) => setEditing({ ...editing, client_phone: e.target.value })} className={inp} /></F>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <F l="Destination"><input value={editing.destination} onChange={(e) => setEditing({ ...editing, destination: e.target.value })} className={inp} /></F>
                <F l="Port"><input value={editing.port} onChange={(e) => setEditing({ ...editing, port: e.target.value })} className={inp} /></F>
                <F l="PO Number"><input value={editing.po_number} onChange={(e) => setEditing({ ...editing, po_number: e.target.value })} className={inp} /></F>
                <F l="Tracking No."><input value={editing.tracking_number} onChange={(e) => setEditing({ ...editing, tracking_number: e.target.value })} className={inp} /></F>
              </div>

              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="label-caps">Line Items</label>
                  <button data-testid="add-line" onClick={() => setEditing({ ...editing, line_items: [...editing.line_items, { ...emptyLine }] })} className="text-xs text-[#4A7C94] hover:text-white flex items-center gap-1"><Plus size={13} /> Add line</button>
                </div>
                <div className="space-y-2">
                  {editing.line_items.map((li, i) => (
                    <div key={i} className="grid grid-cols-12 gap-2 items-center">
                      <input placeholder="Item" data-testid={`line-item-${i}`} value={li.item} onChange={(e) => { const l = [...editing.line_items]; l[i] = { ...l[i], item: e.target.value }; setEditing({ ...editing, line_items: l }); }} className={inp + " col-span-4"} />
                      <input type="number" placeholder="Qty" value={li.qty} onChange={(e) => { const l = [...editing.line_items]; l[i] = { ...l[i], qty: e.target.value }; setEditing({ ...editing, line_items: l }); }} className={inp + " col-span-2"} />
                      <input type="number" placeholder="Unit $" value={li.unit_price} onChange={(e) => { const l = [...editing.line_items]; l[i] = { ...l[i], unit_price: e.target.value }; setEditing({ ...editing, line_items: l }); }} className={inp + " col-span-2"} />
                      <input type="number" placeholder="Fees" value={li.fees} onChange={(e) => { const l = [...editing.line_items]; l[i] = { ...l[i], fees: e.target.value }; setEditing({ ...editing, line_items: l }); }} className={inp + " col-span-1"} />
                      <input type="number" placeholder="Customs" value={li.customs} onChange={(e) => { const l = [...editing.line_items]; l[i] = { ...l[i], customs: e.target.value }; setEditing({ ...editing, line_items: l }); }} className={inp + " col-span-2"} />
                      <button onClick={() => setEditing({ ...editing, line_items: editing.line_items.filter((_, x) => x !== i) })} className="col-span-1 text-[#71717A] hover:text-red-400 flex justify-center"><Trash2 size={14} /></button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <F l="Tax / VAT ($)"><input type="number" value={editing.tax_total} onChange={(e) => setEditing({ ...editing, tax_total: e.target.value })} className={inp} /></F>
                <div className="bg-[#0A0A0B] border border-[#27272A] rounded-sm p-4 text-sm space-y-1">
                  <Row l="Subtotal" v={t.subtotal} /><Row l="Fees" v={t.fees_total} /><Row l="Customs" v={t.customs_total} /><Row l="Tax" v={t.tax_total} />
                  <div className="flex justify-between pt-2 mt-1 border-t border-[#27272A] font-medium text-[#4A7C94]"><span>Grand Total</span><span>${t.grand_total.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span></div>
                </div>
              </div>

              <F l="Notes"><textarea rows={2} value={editing.notes} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} className={inp} /></F>
            </div>
            <div className="flex gap-3 p-6 border-t border-[#27272A] sticky bottom-0 bg-[#121214]">
              <button onClick={() => setEditing(null)} className="flex-1 border border-[#27272A] hover:bg-[#1A1A1D] rounded-sm py-2.5 text-sm transition-colors">Cancel</button>
              <button data-testid="save-doc" onClick={save} className="flex-1 bg-[#4A7C94] hover:bg-[#5A8CA4] rounded-sm py-2.5 text-sm font-medium text-white transition-colors">Save Document</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SendToClient() {
  const [files, setFiles] = useState([]);
  const load = () => api.get("/files?category=send_to_client").then((r) => setFiles(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const remove = async (id) => { if (!window.confirm("Delete file?")) return; await api.delete(`/files/${id}`); load(); toast.success("Deleted"); };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {files.length === 0 && <p className="text-[#71717A] text-sm col-span-full">No generated documents yet. Create a document and click the wand icon to generate a watermarked PDF here.</p>}
      {files.map((f) => (
        <div key={f.id} data-testid={`sent-file-${f.id}`} className="bg-[#121214] border border-[#27272A] rounded-md p-5 flex items-start justify-between">
          <div className="flex items-start gap-3 min-w-0">
            <FileText size={22} className="text-[#4A7C94] shrink-0 mt-0.5" strokeWidth={1.5} />
            <div className="min-w-0">
              <div className="text-sm truncate">{f.original_filename}</div>
              <div className="text-xs text-[#71717A]">{(f.size / 1024).toFixed(0)} KB · {new Date(f.created_at).toLocaleDateString()}</div>
            </div>
          </div>
          <div className="flex gap-1 shrink-0">
            <a data-testid={`download-${f.id}`} href={fileUrl(f.url)} target="_blank" rel="noreferrer" className="text-[#71717A] hover:text-white p-1"><Download size={16} /></a>
            <button onClick={() => remove(f.id)} className="text-[#71717A] hover:text-red-400 p-1"><Trash2 size={16} /></button>
          </div>
        </div>
      ))}
    </div>
  );
}

function F({ l, children }) { return <div><label className="label-caps block mb-2">{l}</label>{children}</div>; }
function Row({ l, v }) { return <div className="flex justify-between text-[#A1A1AA]"><span>{l}</span><span>${(+v || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span></div>; }
