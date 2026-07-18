import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Linkedin, Twitter, Instagram, Mail, Phone, MapPin } from "lucide-react";
import api, { fileUrl } from "@/lib/api";

export function Footer() {
  const [s, setS] = useState({});
  useEffect(() => {
    api.get("/settings").then((r) => setS(r.data)).catch(() => {});
  }, []);

  return (
    <footer data-testid="site-footer" className="relative z-10 border-t border-[#27272A] bg-[#0A0A0B]">
      <div className="max-w-7xl mx-auto px-6 lg:px-12 py-16 grid grid-cols-1 md:grid-cols-4 gap-12">
        <div className="md:col-span-2">
          <div className="font-display text-2xl mb-4">{s.company_name || "Executive Distribution"}</div>
          <p className="text-[#A1A1AA] text-sm max-w-md leading-relaxed">{s.about_text}</p>
          <div className="flex gap-3 mt-6">
            {[["linkedin", Linkedin], ["twitter", Twitter], ["instagram", Instagram]].map(([k, Icon]) => (
              <a key={k} href={s[k] || "#"} data-testid={`social-${k}`}
                 className="h-10 w-10 border border-[#27272A] flex items-center justify-center hover:border-[#4A7C94] hover:text-[#4A7C94] transition-colors">
                <Icon size={16} strokeWidth={1.5} />
              </a>
            ))}
          </div>
        </div>

        <div>
          <div className="label-caps mb-5">Contact</div>
          <ul className="space-y-4 text-sm text-[#A1A1AA]">
            <li className="flex items-center gap-3"><Mail size={15} className="text-[#4A7C94]" />{s.contact_email}</li>
            <li className="flex items-center gap-3"><Phone size={15} className="text-[#4A7C94]" />{s.phone}</li>
            <li className="flex items-start gap-3"><MapPin size={15} className="text-[#4A7C94] mt-0.5" />{s.address}</li>
          </ul>
        </div>

        <div>
          <div className="label-caps mb-5">Company</div>
          <ul className="space-y-3 text-sm text-[#A1A1AA]">
            <li><a href="/#services" className="hover:text-white transition-colors">Services</a></li>
            <li><a href="/#about" className="hover:text-white transition-colors">About</a></li>
            <li><a href="/#contact" className="hover:text-white transition-colors">Request a Quote</a></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-[#27272A] py-6">
        <div className="max-w-7xl mx-auto px-6 lg:px-12 text-xs text-[#71717A] flex flex-col md:flex-row md:items-center justify-between gap-4">
          <span>© {new Date().getFullYear()} {s.company_name || "Executive Distribution"}. All rights reserved.</span>
          <div className="flex items-center gap-6">
            <span className="hidden md:inline">{s.footer_text}</span>
            <Link to="/login" data-testid="footer-admin-logo" aria-label="Admin portal"
              className="group flex items-center justify-center h-9 w-9 rounded-sm border border-[#27272A] hover:border-[#4A7C94] transition-colors overflow-hidden opacity-60 hover:opacity-100">
              {s.logo_url ? (
                <img src={fileUrl(s.logo_url)} alt="admin" className="max-h-full max-w-full object-contain" />
              ) : (
                <span className="font-display text-[#4A7C94] text-sm leading-none">E</span>
              )}
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
