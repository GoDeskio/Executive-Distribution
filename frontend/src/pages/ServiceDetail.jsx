import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Check, ArrowRight } from "lucide-react";
import api from "@/lib/api";
import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Footer";
import { ServiceIcon } from "@/components/site/ServiceIcon";
import { ChatWidget } from "@/components/site/ChatWidget";
import { useSeo } from "@/hooks/useSeo";

export default function ServiceDetail() {
  const { slug } = useParams();
  const [svc, setSvc] = useState(null);
  const [others, setOthers] = useState([]);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);
    api.get(`/services/${slug}`)
      .then((r) => setSvc(r.data))
      .catch(() => setNotFound(true));
    api.get("/services").then((r) => setOthers(r.data)).catch(() => {});
  }, [slug]);

  useSeo({
    title: svc ? (svc.meta_title || svc.title) : undefined,
    description: svc ? (svc.meta_description || svc.short_description) : undefined,
    keywords: svc?.keywords,
    image: svc?.image_url,
    type: "article",
  });

  if (notFound)
    return (
      <div className="grain min-h-screen">
        <Header />
        <div className="max-w-7xl mx-auto px-6 py-40 text-center">
          <h1 className="font-display text-4xl mb-4">Service not found</h1>
          <Link to="/" className="text-[#4A7C94]">← Back home</Link>
        </div>
        <Footer />
      </div>
    );

  if (!svc)
    return <div className="min-h-screen flex items-center justify-center text-[#71717A]">Loading…</div>;

  return (
    <div className="grain">
      <Header />

      <section className="relative min-h-[70vh] flex items-end overflow-hidden">
        <div className="absolute inset-0">
          <img src={svc.image_url} alt={svc.title} className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0A0A0B] via-[#0A0A0B]/75 to-[#0A0A0B]/40" />
        </div>
        <div className="relative z-10 max-w-7xl mx-auto px-6 lg:px-12 pb-20 pt-40 w-full">
          <Link to="/#services" data-testid="back-to-services"
            className="inline-flex items-center gap-2 text-[#A1A1AA] hover:text-white text-sm mb-8 transition-colors">
            <ArrowLeft size={16} /> All Services
          </Link>
          <div className="h-14 w-14 bg-[#0A0A0B]/70 backdrop-blur border border-[#27272A] flex items-center justify-center mb-6">
            <ServiceIcon name={svc.icon} size={26} className="text-[#4A7C94]" strokeWidth={1.5} />
          </div>
          <motion.h1 initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
            className="font-display text-4xl sm:text-5xl lg:text-6xl font-black max-w-4xl leading-[1.05]">
            {svc.title}
          </motion.h1>
        </div>
      </section>

      <section className="relative z-10 max-w-7xl mx-auto px-6 lg:px-12 py-24 grid grid-cols-1 lg:grid-cols-3 gap-16">
        <div className="lg:col-span-2">
          <div className="label-caps mb-4">Overview</div>
          <p className="text-lg text-[#F4F4F5] leading-relaxed mb-8 font-light">{svc.short_description}</p>
          <div className="text-[#A1A1AA] leading-relaxed whitespace-pre-line text-base">{svc.full_description}</div>

          {svc.sections?.map((sec, i) => (
            <div key={i} className="mt-12">
              <h3 className="font-display text-2xl mb-4">{sec.heading}</h3>
              <p className="text-[#A1A1AA] leading-relaxed whitespace-pre-line">{sec.body}</p>
            </div>
          ))}
        </div>

        <aside className="lg:col-span-1">
          <div className="bg-[#121214] border border-[#27272A] p-8 sticky top-28">
            {svc.features?.length > 0 && (
              <>
                <div className="label-caps mb-6">What's Included</div>
                <ul className="space-y-4 mb-8">
                  {svc.features.map((f, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-[#F4F4F5]">
                      <Check size={16} className="text-[#4A7C94] mt-0.5 shrink-0" /> {f}
                    </li>
                  ))}
                </ul>
              </>
            )}
            <a href="/#contact" data-testid="service-cta"
               className="w-full bg-[#4A7C94] hover:bg-[#5A8CA4] transition-colors text-white px-6 py-4 rounded-sm font-medium flex items-center justify-center gap-2">
              Request This Service <ArrowRight size={16} />
            </a>
          </div>
        </aside>
      </section>

      {others.filter((o) => o.slug !== svc.slug).length > 0 && (
        <section className="relative z-10 border-t border-[#27272A]">
          <div className="max-w-7xl mx-auto px-6 lg:px-12 py-20">
            <div className="label-caps mb-8">More Programs</div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {others.filter((o) => o.slug !== svc.slug).slice(0, 3).map((o) => (
                <Link key={o.id} to={`/services/${o.slug}`}
                  className="group bg-[#121214] border border-[#27272A] overflow-hidden hover:border-[#4A7C94] transition-colors">
                  <div className="h-36 overflow-hidden">
                    <img src={o.image_url} alt={o.title}
                      className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500" />
                  </div>
                  <div className="p-6">
                    <h4 className="font-display text-lg group-hover:text-[#4A7C94] transition-colors">{o.title}</h4>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      <Footer />
      <ChatWidget />
    </div>
  );
}
