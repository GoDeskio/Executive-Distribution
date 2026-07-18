import { useEffect, useState } from "react";
import { Sparkles, Calculator as CalcIcon, Cpu } from "lucide-react";
import api from "@/lib/api";
import { AdminHeader } from "./AdminHeader";
import { Chat } from "@/components/Chat";

const inp = "w-full bg-[#0A0A0B] border border-[#27272A] focus:border-[#4A7C94] outline-none rounded-sm px-3 py-2.5 text-sm transition-colors";

export default function AiAssistant() {
  const [tab, setTab] = useState("assistant");
  const [status, setStatus] = useState(null);

  useEffect(() => { api.get("/ai/status").then((r) => setStatus(r.data)).catch(() => {}); }, []);

  return (
    <div className="flex flex-col h-screen">
      <AdminHeader title="AI Assistant" subtitle="Logistics calculator & documentation expert">
        {status && (
          <div className="flex items-center gap-2 text-xs text-[#71717A]" data-testid="ai-status">
            <Cpu size={14} className="text-[#4A7C94]" />
            {status.provider}/{status.model} · {status.source === "own" ? "your key" : "Emergent"}
          </div>
        )}
      </AdminHeader>

      <div className="px-8 pt-6">
        <div className="flex gap-1 border-b border-[#27272A]">
          {[["assistant", "Assistant", Sparkles], ["calculator", "Fee Calculator", CalcIcon]].map(([k, l, Icon]) => (
            <button key={k} data-testid={`ai-tab-${k}`} onClick={() => setTab(k)}
              className={`flex items-center gap-2 px-5 py-3 text-sm border-b-2 -mb-px transition-colors ${tab === k ? "border-[#4A7C94] text-[#4A7C94]" : "border-transparent text-[#A1A1AA] hover:text-white"}`}>
              <Icon size={15} /> {l}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-hidden p-8">
        {tab === "assistant" ? (
          <div className="h-full bg-[#121214] border border-[#27272A] rounded-md overflow-hidden">
            <Chat endpoint="/ai/chat/admin" scope="admin"
              placeholder="e.g. Calculate duties for $20k of cigars, 300kg, to Miami by ocean…"
              suggestions={[
                "Which documents are required to import cigars into the US?",
                "Break down fees for 500kg coffee, $15,000 value, air freight",
                "Draft a quote summary for a Larimar shipment to Europe",
              ]} />
          </div>
        ) : <Calculator />}
      </div>
    </div>
  );
}

function Calculator() {
  const [form, setForm] = useState({ item_name: "", declared_value: "", weight_kg: "", quantity: 1, origin: "", destination: "", mode: "ocean" });
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const run = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/calculate", {
        ...form,
        declared_value: +form.declared_value || 0,
        weight_kg: +form.weight_kg || 0,
        quantity: +form.quantity || 1,
      });
      setResult(data);
    } finally { setBusy(false); }
  };

  const rows = result ? [
    ["Declared value", result.breakdown.declared_value],
    ["Freight", result.breakdown.freight],
    ["Handling", result.breakdown.handling],
    ["Port surcharge", result.breakdown.port_surcharge],
    ["Insurance", result.breakdown.insurance],
    ["Customs duty", result.breakdown.customs_duty],
    ["Tax / VAT", result.breakdown.vat_tax],
  ] : [];

  return (
    <div className="h-full overflow-y-auto grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-[#121214] border border-[#27272A] rounded-md p-6 space-y-4">
        <div className="label-caps">Shipment Details</div>
        <div><label className="label-caps block mb-2">Item</label><input data-testid="calc-item" value={form.item_name} onChange={set("item_name")} className={inp} placeholder="e.g. Premium cigars" /></div>
        <div className="grid grid-cols-2 gap-4">
          <div><label className="label-caps block mb-2">Declared Value ($)</label><input data-testid="calc-value" type="number" value={form.declared_value} onChange={set("declared_value")} className={inp} /></div>
          <div><label className="label-caps block mb-2">Weight (kg)</label><input data-testid="calc-weight" type="number" value={form.weight_kg} onChange={set("weight_kg")} className={inp} /></div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div><label className="label-caps block mb-2">Quantity</label><input type="number" value={form.quantity} onChange={set("quantity")} className={inp} /></div>
          <div><label className="label-caps block mb-2">Mode</label>
            <select data-testid="calc-mode" value={form.mode} onChange={set("mode")} className={inp}>
              <option value="ocean">Ocean freight</option><option value="air">Air freight</option><option value="ground">Ground</option>
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div><label className="label-caps block mb-2">Origin</label><input value={form.origin} onChange={set("origin")} className={inp} /></div>
          <div><label className="label-caps block mb-2">Destination</label><input data-testid="calc-dest" value={form.destination} onChange={set("destination")} className={inp} /></div>
        </div>
        <button data-testid="calc-run" onClick={run} disabled={busy}
          className="w-full bg-[#4A7C94] hover:bg-[#5A8CA4] disabled:opacity-60 text-white py-3 rounded-sm font-medium transition-colors">
          {busy ? "Calculating…" : "Calculate Fees"}
        </button>
      </div>

      <div className="bg-[#121214] border border-[#27272A] rounded-md p-6">
        <div className="label-caps mb-5">Estimate</div>
        {!result ? <p className="text-[#71717A] text-sm">Enter shipment details and calculate to see a fee breakdown.</p> : (
          <div data-testid="calc-result">
            <div className="space-y-2 mb-5">
              {rows.map(([l, v]) => (
                <div key={l} className="flex justify-between text-sm border-b border-[#27272A]/50 py-2">
                  <span className="text-[#A1A1AA]">{l}</span>
                  <span>${v.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                </div>
              ))}
            </div>
            <div className="flex justify-between items-center bg-[#4A7C94]/10 border border-[#4A7C94]/30 rounded-sm px-4 py-4">
              <span className="font-display text-lg">Grand Total</span>
              <span className="font-display text-2xl text-[#4A7C94]">${result.grand_total.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>
            <p className="text-xs text-[#71717A] mt-4">Rule-based estimate. Use the Assistant tab to ask which documents are required for this shipment.</p>
          </div>
        )}
      </div>
    </div>
  );
}
