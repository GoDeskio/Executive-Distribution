import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, ArrowUpRight, Globe2, ShieldCheck, Timer, Mail, Phone, MapPin } from "lucide-react";
import api from "@/lib/api";
import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Footer";
import { ServiceIcon } from "@/components/site/ServiceIcon";
import { QuoteForm } from "@/components/site/QuoteForm";

const fade = {
  hidden: { opacity: 0, y: 30 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.6, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] } }),
};

export default function Home() {
  const [services, setServices] = useState([]);
  const [s, setS] = useState({});

  useEffect(() => {
    api.get("/services").then((r) => setServices(r.data)).catch(() => {});
    api.get("/settings").then((r) => {
      setS(r.data);
      if (r.data.seo_title) document.title = r.data.seo_title;
    }).catch(() => {});
  }, []);

  return (
    <div className="grain">
      <Header />

      {/* HERO */}
      <section className="relative min-h-[92vh] flex items-end overflow-hidden">
        <div className="absolute inset-0">
          <img src={s.hero_image} alt="hero" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0A0A0B] via-[#0A0A0B]/70 to-[#0A0A0B]/30" />
          <div className="absolute inset-0 bg-[#0A0A0B]/30" />
        </div>
        <div className="relative z-10 max-w-7xl mx-auto px-6 lg:px-12 pb-24 pt-40 w-full">
          <motion.div initial="hidden" animate="show" variants={fade} className="label-caps mb-6">
            {s.tagline || "Global Sourcing. Executive Delivery."}
          </motion.div>
          <motion.h1 initial="hidden" animate="show" custom={1} variants={fade}
            className="font-display text-4xl sm:text-5xl lg:text-6xl font-black leading-[1.05] max-w-4xl">
            {s.hero_title || "Moving the World's Finest Goods With Executive Precision"}
          </motion.h1>
          <motion.p initial="hidden" animate="show" custom={2} variants={fade}
            className="text-[#A1A1AA] text-base sm:text-lg max-w-2xl mt-8 leading-relaxed">
            {s.hero_subtitle}
          </motion.p>
          <motion.div initial="hidden" animate="show" custom={3} variants={fade} className="flex flex-wrap gap-4 mt-10">
            <a href="#services" data-testid="hero-cta"
               className="group bg-[#4A7C94] hover:bg-[#5A8CA4] transition-colors text-white px-7 py-4 rounded-sm font-medium flex items-center gap-2">
              {s.hero_cta || "Explore Our Services"}
              <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
            </a>
            <a href="#contact"
               className="border border-[#27272A] hover:bg-[#1A1A1D] transition-colors px-7 py-4 rounded-sm font-medium">
              Request a Quote
            </a>
          </motion.div>
        </div>
      </section>

      {/* STATS */}
      <section className="relative z-10 border-y border-[#27272A] bg-[#0A0A0B]">
        <div className="max-w-7xl mx-auto px-6 lg:px-12 grid grid-cols-2 md:grid-cols-4 divide-x divide-[#27272A]">
          {[["24+", "Years Operating"], ["60+", "Countries Served"], ["1.2M", "TEU Shipped"], ["99.4%", "On-Time Delivery"]].map(
            ([n, l], i) => (
              <div key={i} className="py-10 px-6 text-center">
                <div className="font-display text-3xl sm:text-4xl">{n}</div>
                <div className="text-[#71717A] text-xs tracking-wide mt-2 uppercase">{l}</div>
              </div>
            )
          )}
        </div>
      </section>

      {/* SERVICES */}
      <section id="services" className="relative z-10 max-w-7xl mx-auto px-6 lg:px-12 py-28">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-16">
          <div>
            <div className="label-caps mb-4">Programs & Services</div>
            <h2 className="font-display text-3xl sm:text-4xl font-bold max-w-2xl leading-tight">
              A full-service sourcing house built for discerning importers.
            </h2>
          </div>
          <p className="text-[#A1A1AA] max-w-sm text-sm leading-relaxed">
            From ocean freight to rare commodities, every program is managed end-to-end by dedicated distribution specialists.
          </p>
        </div>

        <div className="grid grid-cols-12 gap-8">
          {services.map((svc, i) => (
            <motion.div key={svc.id} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-80px" }}
              custom={i % 3} variants={fade} className="col-span-12 md:col-span-6 lg:col-span-4">
              <Link to={`/services/${svc.slug}`} data-testid={`service-card-${svc.slug}`}
                className="block h-full bg-[#121214] border border-[#27272A] overflow-hidden group transition-all duration-300 hover:-translate-y-1 hover:border-[#4A7C94]">
                <div className="h-52 w-full overflow-hidden relative">
                  <img src={svc.image_url} alt={svc.title}
                    className="w-full h-full object-cover grayscale group-hover:grayscale-0 group-hover:scale-105 transition-all duration-700" />
                  <div className="absolute top-4 left-4 h-10 w-10 bg-[#0A0A0B]/80 backdrop-blur border border-[#27272A] flex items-center justify-center">
                    <ServiceIcon name={svc.icon} size={18} className="text-[#4A7C94]" strokeWidth={1.5} />
                  </div>
                </div>
                <div className="p-8">
                  <h3 className="font-display text-xl mb-3 group-hover:text-[#4A7C94] transition-colors">{svc.title}</h3>
                  <p className="text-[#A1A1AA] text-sm leading-relaxed mb-6">{svc.short_description}</p>
                  <span className="inline-flex items-center gap-2 text-[#4A7C94] text-sm font-medium">
                    View Program <ArrowUpRight size={16} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                  </span>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ABOUT */}
      <section id="about" className="relative z-10 border-t border-[#27272A]">
        <div className="max-w-7xl mx-auto px-6 lg:px-12 py-28 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <motion.div initial="hidden" whileInView="show" viewport={{ once: true }} variants={fade}>
            <div className="label-caps mb-4">Who We Are</div>
            <h2 className="font-display text-3xl sm:text-4xl font-bold leading-tight mb-6">
              Precision meets discretion in every shipment.
            </h2>
            <p className="text-[#A1A1AA] leading-relaxed mb-8">{s.about_text}</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              {[[Globe2, "Global Network"], [ShieldCheck, "Fully Compliant"], [Timer, "On-Time, Every Time"]].map(
                ([Icon, l], i) => (
                  <div key={i} className="flex items-center gap-3">
                    <Icon size={22} className="text-[#4A7C94]" strokeWidth={1.5} />
                    <span className="text-sm text-[#F4F4F5]">{l}</span>
                  </div>
                )
              )}
            </div>
          </motion.div>
          <motion.div initial="hidden" whileInView="show" viewport={{ once: true }} custom={1} variants={fade}
            className="relative">
            <img src={s.about_image} alt="about"
              className="w-full h-[480px] object-cover border border-[#27272A]" />
            <div className="absolute -bottom-6 -left-6 hidden sm:block bg-[#4A7C94] text-white p-6 max-w-[220px]">
              <div className="font-display text-3xl">$4.8B</div>
              <div className="text-xs uppercase tracking-wide mt-1 text-white/80">Goods moved annually</div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* QUOTE / CONTACT */}
      <section id="contact" className="relative z-10 border-t border-[#27272A] bg-[#121214]">
        <div className="max-w-7xl mx-auto px-6 lg:px-12 py-28 grid grid-cols-1 lg:grid-cols-2 gap-16 items-start">
          <div className="lg:sticky lg:top-28">
            <div className="label-caps mb-4">Request a Quote</div>
            <h2 className="font-display text-3xl sm:text-4xl font-bold leading-tight max-w-md">
              Tell us what you need moved or sourced.
            </h2>
            <p className="text-[#A1A1AA] mt-6 leading-relaxed max-w-md">
              Share a few details and reference images. An Executive Distribution specialist will assess your
              requirements and respond with a tailored plan — discreetly and without obligation.
            </p>
            <div className="mt-8 space-y-4">
              <div className="flex items-center gap-3 text-sm text-[#A1A1AA]"><Mail size={16} className="text-[#4A7C94]" />{s.contact_email}</div>
              <div className="flex items-center gap-3 text-sm text-[#A1A1AA]"><Phone size={16} className="text-[#4A7C94]" />{s.phone}</div>
              <div className="flex items-center gap-3 text-sm text-[#A1A1AA]"><MapPin size={16} className="text-[#4A7C94]" />{s.address}</div>
            </div>
          </div>
          <QuoteForm />
        </div>
      </section>

      <Footer />
    </div>
  );
}
