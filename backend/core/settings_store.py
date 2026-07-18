from fastapi import Request
from core.db import db

DEFAULT_FEE_RULES = {
    "freight_rate_per_kg": 4.5,
    "handling_fee_flat": 75.0,
    "insurance_pct": 1.5,
    "duty_pct": 8.0,
    "vat_pct": 5.0,
    "port_surcharge": 120.0,
}

PUBLIC_SYSTEM = (
    "You are the Executive Distribution AI concierge on a premium import/export & product sourcing "
    "company website. You help visitors estimate shipping fees, explain which documents they will need "
    "for customs/shipping, and answer questions about services (freight forwarding, port logistics, "
    "cigar sourcing, coffee distribution, Larimar/mineral supply, warehousing). Be concise, professional "
    "and helpful. When a visitor wants a formal quote, encourage them to submit the Request a Quote form "
    "with item details, destination and reference images. Never invent client data. Give fee figures as "
    "clearly-labeled estimates."
)

ADMIN_SYSTEM = (
    "You are the Executive Distribution operations assistant for staff. You act as a logistics calculator "
    "and documentation expert: compute and explain shipping fees, customs duties and taxes, and list the "
    "exact documents required for a given shipment (e.g. commercial invoice, packing list, bill of lading, "
    "certificate of origin, import/export licenses, insurance certificate, phytosanitary/CITES where relevant). "
    "Help draft quotes and receipts and organize records per client. Be precise, use clear line-item "
    "breakdowns, and state assumptions."
)


async def get_settings_doc():
    doc = await db.settings.find_one({"_id": "site"}) or {}
    doc.pop("_id", None)
    return doc


def resolve_base_url(settings: dict, request: Request) -> str:
    base = (settings.get("site_url") or "").strip().rstrip("/")
    if base:
        return base
    fwd_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    fwd_proto = request.headers.get("x-forwarded-proto", "https")
    if fwd_host:
        return f"{fwd_proto}://{fwd_host}"
    return str(request.base_url).rstrip("/")


DEFAULT_SERVICES = [
    {"title": "Global Import & Export", "icon": "ship",
     "image_url": "https://images.unsplash.com/photo-1568347877321-f8935c7dc5a3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA0MTJ8MHwxfHNlYXJjaHwxfHxjYXJnbyUyMHNoaXAlMjBmcmVpZ2h0ZXIlMjBuaWdodHxlbnwwfHx8fDE3ODQzOTA0Njd8MA&ixlib=rb-4.1.0&q=85",
     "short_description": "End-to-end freight forwarding across every major trade lane, handled with executive precision.",
     "full_description": "Executive Distribution moves cargo across oceans with the discipline of a private logistics firm. From documentation and customs clearance to last-mile delivery, we orchestrate the full lifecycle of your international shipments. Our network of carriers, brokers, and bonded warehouses ensures your goods arrive intact, compliant, and on schedule.",
     "features": ["Ocean & air freight forwarding", "Customs brokerage & compliance", "Bonded warehousing", "Real-time shipment tracking"]},
    {"title": "Port & Logistics Management", "icon": "anchor",
     "image_url": "https://images.unsplash.com/photo-1554769944-3138b076c38a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzV8MHwxfHNlYXJjaHwxfHxpbmR1c3RyaWFsJTIwcG9ydCUyMGRyb25lfGVufDB8fHx8MTc4NDM5MDQ2N3ww&ixlib=rb-4.1.0&q=85",
     "short_description": "Container handling, drayage and terminal coordination at the world's busiest ports.",
     "full_description": "Our port operations team manages terminal relationships, container drayage, and yard coordination so your freight never sits idle. We negotiate priority berthing, optimize container turnaround, and provide transparent reporting at every touchpoint.",
     "features": ["Terminal & berth coordination", "Container drayage", "Yard & inventory management", "Demurrage mitigation"]},
    {"title": "Premium Cigar Sourcing", "icon": "flame",
     "image_url": "https://images.pexels.com/photos/3975055/pexels-photo-3975055.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
     "short_description": "Direct-from-factory sourcing of hand-rolled cigars from the Caribbean's finest houses.",
     "full_description": "We maintain direct relationships with heritage cigar factories, giving our clients access to limited allocations of hand-rolled, aged tobacco. Every shipment is climate-controlled, authenticated, and fully documented for import.",
     "features": ["Factory-direct allocations", "Climate-controlled transport", "Authentication & grading", "Full import documentation"]},
    {"title": "Coffee Bean Distribution", "icon": "coffee",
     "image_url": "https://images.unsplash.com/photo-1606486544554-164d98da4889?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1MDV8MHwxfHNlYXJjaHwzfHxjb2ZmZWUlMjBiZWFuJTIwZGlzdHJpYnV0aW9ufGVufDB8fHx8MTc4NDM5MDQ2N3ww&ixlib=rb-4.1.0&q=85",
     "short_description": "Single-origin green coffee, sourced ethically and delivered at scale to roasters worldwide.",
     "full_description": "From highland estates to your roastery, we manage the sourcing, grading, and logistics of premium green coffee. Our traceable supply chain guarantees quality and ethical origin at commercial volumes.",
     "features": ["Single-origin sourcing", "Cupping & grading", "Traceable supply chain", "Volume contracts"]},
    {"title": "Larimar & Mineral Supply", "icon": "gem",
     "image_url": "https://images.unsplash.com/photo-1767131545090-e13ae86c8e13?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzJ8MHwxfHNlYXJjaHwzfHxibHVlJTIwZ2Vtc3RvbmUlMjByb3VnaHxlbnwwfHx8fDE3ODQzOTA0NzR8MA&ixlib=rb-4.1.0&q=85",
     "short_description": "Exclusive access to rare Larimar and semi-precious minerals from protected sources.",
     "full_description": "As one of few distributors with licensed access to Larimar mines, we supply raw and polished stone to jewelers and collectors. Each lot is certified for authenticity and origin.",
     "features": ["Licensed mine access", "Raw & polished lots", "Authenticity certification", "Export licensing"]},
    {"title": "Warehousing & Fulfillment", "icon": "warehouse",
     "image_url": "https://images.pexels.com/photos/4487365/pexels-photo-4487365.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
     "short_description": "Secure distribution centers with real-time inventory and white-glove fulfillment.",
     "full_description": "Our distribution centers combine secure storage with intelligent inventory systems and hands-on fulfillment teams. Whether you need bulk staging or pick-and-pack, our managers treat your goods as their own.",
     "features": ["Secure climate storage", "Real-time inventory", "Pick, pack & ship", "Dedicated account managers"]},
]

DEFAULT_SETTINGS = {
    "company_name": "Executive Distribution",
    "logo_url": "",
    "tagline": "Global Sourcing. Executive Delivery.",
    "hero_title": "Moving the World's Finest Goods With Executive Precision",
    "hero_subtitle": "Executive Distribution is a private import/export and product sourcing firm connecting discerning clients to premium goods across the globe — freight, logistics, and rare commodities under one roof.",
    "hero_image": "https://images.pexels.com/photos/14734004/pexels-photo-14734004.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "hero_cta": "Explore Our Services",
    "about_text": "For over two decades, Executive Distribution has quietly powered the supply chains of luxury brands, boutique roasters, jewelers, and importers. We operate where precision meets discretion.",
    "about_image": "https://images.pexels.com/photos/4487365/pexels-photo-4487365.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "contact_email": "contact@executivedistribution.com",
    "phone": "+1 (305) 555-0142",
    "address": "1200 Brickell Bay Drive, Miami, FL",
    "linkedin": "#", "twitter": "#", "instagram": "#",
    "footer_text": "Executive Distribution — Global import/export & product sourcing.",
    "seo_title": "Executive Distribution | Global Import, Export & Product Sourcing",
    "seo_description": "Premium import/export and product sourcing. Freight forwarding, port logistics, cigars, coffee, Larimar and warehousing — handled with executive precision.",
    "seo_keywords": "import export, product sourcing, freight forwarding, cigar sourcing, coffee distribution, larimar supply, warehousing",
    "ai_provider": "openai",
    "ai_model": "gpt-5.4",
    "ai_use_own_key": False,
    "ai_own_key": "",
    "fee_rules": dict(DEFAULT_FEE_RULES),
    "email_provider": "none",
    "email_api_key": "",
    "email_from": "",
    "slack_webhook_url": "",
    "alert_on_approval": False,
    "social_login_enabled": False,
    "stytch_project_id": "",
    "stytch_secret": "",
    "site_url": "",
    "page_seo": [],
    "lockout_max_attempts": 5,
    "lockout_minutes": 15,
    "search_engine_ping_enabled": False,
    "indexnow_key": "",
    "update_repo_url": "",
    "update_branch": "main",
    "update_token": "",
    "update_auto_check": True,
    "update_auto_apply": False,
    "update_current_version": "",
    "backup_dir": "",
    "backup_include_files": True,
    "backup_auto_before_update": True,
    "backup_schedule_enabled": False,
    "backup_schedule_interval_hours": 24,
    "backup_retention": 7,
}
