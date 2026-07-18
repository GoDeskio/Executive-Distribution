import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { FileText, Download, ShieldCheck, Mail, Phone } from "lucide-react";
import api, { fileUrl } from "@/lib/api";

const DTYPE = { quote: "Quote", receipt: "Receipt", customs: "Customs Doc" };

export default function Portal() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.get(`/portal/${token}`)
      .then((r) => { setData(r.data); document.title = `${r.data.company.name} · Client Portal`; })
      .catch(() => setError(true));
  }, [token]);

  if (error)
    return (
      <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center p-6 text-center">
        <div>
          <h1 className="font-display text-3xl mb-3">Portal unavailable</h1>
          <p className="text-[#71717A]">This link is invalid or has been revoked. Please contact us for an updated link.</p>
        </div>
      </div>
    );

  if (!data) return <div className="min-h-screen flex items-center justify-center text-[#71717A]">Loading…</div>;

  const { client, company, documents } = data;

  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F4F4F5]">
      <header className="border-b border-[#27272A]">
        <div className="max-w-4xl mx-auto px-6 py-6 flex items-center gap-3">
          {company.logo_url ? (
            <img src={fileUrl(company.logo_url)} alt="logo" className="h-9 w-auto object-contain" />
          ) : (
            <div className="h-9 w-9 border border-[#4A7C94] flex items-center justify-center"><span className="font-display text-[#4A7C94]">E</span></div>
          )}
          <div>
            <div className="font-display text-lg leading-tight">{company.name}</div>
            <div className="text-xs text-[#71717A]">{company.tagline}</div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-14">
        <div className="flex items-center gap-2 label-caps mb-4"><ShieldCheck size={14} /> Secure Client Portal</div>
        <h1 className="font-display text-3xl sm:text-4xl font-bold mb-2">Welcome, {client.name}</h1>
        {client.company && <p className="text-[#A1A1AA] mb-10">{client.company}</p>}

        <div className="label-caps mb-4">Your Documents ({documents.length})</div>
        {documents.length === 0 ? (
          <div className="bg-[#121214] border border-[#27272A] rounded-md p-12 text-center text-[#71717A]">
            No documents have been shared with you yet. Check back soon.
          </div>
        ) : (
          <div className="space-y-3">
            {documents.map((d, i) => (
              <div key={i} data-testid={`portal-doc-${i}`} className="bg-[#121214] border border-[#27272A] rounded-md p-5 flex items-center justify-between hover:border-[#4A7C94] transition-colors">
                <div className="flex items-center gap-4 min-w-0">
                  <FileText size={22} className="text-[#4A7C94] shrink-0" strokeWidth={1.5} />
                  <div className="min-w-0">
                    <div className="font-medium">{d.number} · {DTYPE[d.doc_type] || d.doc_type}</div>
                    <div className="text-xs text-[#71717A]">
                      {d.date}{d.destination ? ` · ${d.destination}` : ""}{d.port ? ` · ${d.port}` : ""} · ${(d.grand_total || 0).toLocaleString()}
                    </div>
                  </div>
                </div>
                <a data-testid={`portal-download-${i}`} href={fileUrl(d.download_url)} target="_blank" rel="noreferrer"
                  className="shrink-0 flex items-center gap-2 bg-[#4A7C94] hover:bg-[#5A8CA4] text-white text-sm px-4 py-2.5 rounded-sm transition-colors">
                  <Download size={16} /> Download
                </a>
              </div>
            ))}
          </div>
        )}

        <div className="mt-14 pt-8 border-t border-[#27272A] text-sm text-[#A1A1AA] flex flex-wrap gap-6">
          {company.contact_email && <span className="flex items-center gap-2"><Mail size={15} className="text-[#4A7C94]" />{company.contact_email}</span>}
          {company.phone && <span className="flex items-center gap-2"><Phone size={15} className="text-[#4A7C94]" />{company.phone}</span>}
        </div>
      </main>
    </div>
  );
}
