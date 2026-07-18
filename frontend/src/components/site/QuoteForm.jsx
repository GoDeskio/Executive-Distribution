import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { Send, Upload, X, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

const inp =
  "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-4 py-3 text-sm transition-colors placeholder:text-[#52525B]";

const EMPTY = { name: "", email: "", company: "", phone: "", destination: "", description: "" };

export function QuoteForm() {
  const [form, setForm] = useState(EMPTY);
  const [images, setImages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const fileRef = useRef();

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const addImages = (files) => {
    const arr = [...files].slice(0, 4 - images.length);
    setImages((prev) => [...prev, ...arr].slice(0, 4));
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim()) return toast.error("Name and email are required");
    setBusy(true);
    const fd = new FormData();
    Object.entries(form).forEach(([k, v]) => fd.append(k, v));
    images.forEach((img) => fd.append("images", img));
    try {
      await api.post("/quotes", fd);
      setDone(true);
      setForm(EMPTY);
      setImages([]);
      toast.success("Request submitted — our team will be in touch.");
    } catch (err) {
      toast.error("Could not submit request. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  if (done)
    return (
      <div data-testid="quote-success" className="bg-[#121214] border border-[#27272A] rounded-md p-12 text-center">
        <CheckCircle2 size={48} className="text-[#4A7C94] mx-auto mb-6" strokeWidth={1.3} />
        <h3 className="font-display text-2xl mb-3">Request received</h3>
        <p className="text-[#A1A1AA] max-w-md mx-auto">
          Thank you. An Executive Distribution specialist will review your request and contact you shortly.
        </p>
        <button onClick={() => setDone(false)} data-testid="quote-new"
          className="mt-8 border border-[#27272A] hover:border-[#4A7C94] px-6 py-3 rounded-sm text-sm transition-colors">
          Submit another request
        </button>
      </div>
    );

  return (
    <motion.form onSubmit={submit} data-testid="quote-form"
      initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
      className="bg-[#121214] border border-[#27272A] rounded-md p-8 space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <div>
          <label className="label-caps block mb-2">Name *</label>
          <input data-testid="quote-name" value={form.name} onChange={set("name")} required className={inp} placeholder="Your full name" />
        </div>
        <div>
          <label className="label-caps block mb-2">Email *</label>
          <input data-testid="quote-email" type="email" value={form.email} onChange={set("email")} required className={inp} placeholder="you@company.com" />
        </div>
        <div>
          <label className="label-caps block mb-2">Company</label>
          <input data-testid="quote-company" value={form.company} onChange={set("company")} className={inp} placeholder="Company name" />
        </div>
        <div>
          <label className="label-caps block mb-2">Phone</label>
          <input data-testid="quote-phone" value={form.phone} onChange={set("phone")} className={inp} placeholder="+1 (000) 000-0000" />
        </div>
      </div>

      <div>
        <label className="label-caps block mb-2">Shipping Destination</label>
        <input data-testid="quote-destination" value={form.destination} onChange={set("destination")} className={inp} placeholder="Where should the items be shipped?" />
      </div>

      <div>
        <label className="label-caps block mb-2">Item / Request Description</label>
        <textarea data-testid="quote-description" rows={4} value={form.description} onChange={set("description")} className={inp}
          placeholder="Describe the item(s) you'd like sourced or shipped, quantities, timelines…" />
      </div>

      <div>
        <label className="label-caps block mb-2">Reference Images (up to 4)</label>
        <div className="flex flex-wrap gap-3">
          {images.map((img, i) => (
            <div key={i} className="relative h-20 w-20 rounded-sm overflow-hidden border border-[#27272A]">
              <img src={URL.createObjectURL(img)} alt="" className="h-full w-full object-cover" />
              <button type="button" onClick={() => setImages(images.filter((_, x) => x !== i))}
                className="absolute top-0.5 right-0.5 bg-[#0A0A0B]/80 rounded-full p-0.5 hover:text-red-400">
                <X size={13} />
              </button>
            </div>
          ))}
          {images.length < 4 && (
            <button type="button" onClick={() => fileRef.current?.click()} data-testid="quote-image-btn"
              className="h-20 w-20 border border-dashed border-[#27272A] hover:border-[#4A7C94] rounded-sm flex flex-col items-center justify-center gap-1 text-[#71717A] hover:text-[#4A7C94] transition-colors">
              <Upload size={16} />
              <span className="text-[10px]">Add</span>
            </button>
          )}
          <input ref={fileRef} type="file" accept="image/*" multiple className="hidden"
            data-testid="quote-image-input" onChange={(e) => e.target.files.length && addImages(e.target.files)} />
        </div>
      </div>

      <button type="submit" disabled={busy} data-testid="quote-submit"
        className="w-full bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-60 transition-colors text-white px-6 py-4 rounded-sm font-medium flex items-center justify-center gap-2">
        {busy ? "Submitting…" : "Submit Request"} {!busy && <Send size={16} />}
      </button>
    </motion.form>
  );
}
