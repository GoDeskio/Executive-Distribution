import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import api, { fileUrl } from "@/lib/api";

export function Header() {
  const [settings, setSettings] = useState({});
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();

  useEffect(() => {
    api.get("/settings").then((r) => setSettings(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => setOpen(false), [location.pathname]);

  const links = [
    { label: "Home", to: "/" },
    { label: "Services", to: "/#services" },
    { label: "About", to: "/#about" },
    { label: "Contact", to: "/#contact" },
  ];

  return (
    <header
      data-testid="site-header"
      className={`fixed top-0 inset-x-0 z-50 transition-colors duration-300 border-b ${
        scrolled ? "backdrop-blur-xl bg-[#0A0A0B]/85 border-[#27272A]" : "bg-transparent border-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-12 h-20 flex items-center justify-between">
        <Link to="/" data-testid="logo-link" className="flex items-center gap-3">
          {settings.logo_url ? (
            <img src={fileUrl(settings.logo_url)} alt="logo" className="h-12 w-auto object-contain" />
          ) : (
            <div className="h-9 w-9 border border-[#4A7C94] flex items-center justify-center">
              <span className="font-display text-[#4A7C94] text-lg leading-none">E</span>
            </div>
          )}
          <div className="leading-tight">
            <div className="font-display text-lg tracking-wide">{settings.company_name || "Executive Distribution"}</div>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-10">
          {links.map((l) => (
            <a key={l.label} href={l.to} data-testid={`nav-${l.label.toLowerCase()}`}
               className="text-sm text-[#A1A1AA] hover:text-white transition-colors tracking-wide">
              {l.label}
            </a>
          ))}
          <a href="/#contact" data-testid="header-cta"
             className="bg-[#4A7C94] hover:bg-[#5A8CA4] transition-colors text-white text-sm px-5 py-2.5 rounded-sm font-medium">
            Request a Quote
          </a>
        </nav>

        <button data-testid="mobile-menu-toggle" className="md:hidden text-white" onClick={() => setOpen(!open)}>
          {open ? <X /> : <Menu />}
        </button>
      </div>

      {open && (
        <div className="md:hidden bg-[#0A0A0B]/95 backdrop-blur-xl border-t border-[#27272A] px-6 py-4 flex flex-col gap-4">
          {links.map((l) => (
            <a key={l.label} href={l.to} className="text-[#A1A1AA] hover:text-white">{l.label}</a>
          ))}
          <a href="/#contact" className="bg-[#4A7C94] text-white px-5 py-2.5 rounded-sm text-center">Request a Quote</a>
        </div>
      )}
    </header>
  );
}
