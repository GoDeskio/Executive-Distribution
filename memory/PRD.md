# Executive Distribution — PRD

## Original Problem Statement
Build a fully dynamic, professional website "Executive Distribution" (Import/Export & product sourcing company): Hero home page; program/service cards (image on top, title, short description) linking to full description pages controlled/edited from an admin dashboard; full admin dashboard with SEO controls for the whole site, a functional CRM (clients, visitors, documents), a left sidebar (settings, profile, object storage for assets & documents); a visitor activity heatmap monitored in admin. Dark masculine steel-blue palette, expensive look; logos editable from admin.

## User Choices
- Auth: JWT email + password
- Heatmap: click heatmap overlay + visitor analytics (both)
- Scope: full build (Services + SEO + CRM + assets)
- Images: mix of real stock + curated
- Accent: steel blue / gunmetal

## Architecture
- Backend: FastAPI + MongoDB (motor). JWT (bcrypt) auth, Bearer token. Emergent object storage for assets/documents. Routes under /api.
- Frontend: React 19 + Tailwind + shadcn + framer-motion + recharts. Token in localStorage (`ed_token`).
- Design: `/app/design_guidelines.json` (Playfair Display + Manrope, obsidian + steel blue).

## Implemented (2026-06)
- **Approval alerts + social login connect:** Settings → Integrations now has Slack approval alerts (webhook + "alert on approval" toggle; fires a best-effort Slack message when a client approves a quote, run off the event loop) and a **Stytch** social-login connect option (project id + secret + enable toggle, saved for later). All secrets sanitized from the API.
- **Client Portal:** tokenized private link (no login) to view/download quotes/receipts, one-click **quote approval** → admin notification (bell + Dashboard Recent Activity), per-document share toggle, link expiry.
- **HS/tariff codes:** AI-suggested per line item; editable; on the PDF.
- **AI Refine/Regenerate:** inside the quote editor, an instruction box regenerates the draft (line items, totals, docs) via the AI.
- **Direct PDF download:** generated documents are downloadable straight from the document row (and the Send-to-Client folder).
- **Integrations (saved for later):** Settings → Integrations lets admin connect an email service (Resend/SendGrid) — provider, from-email, API key stored server-side (secrets never exposed via API). Actual email sending is NOT enabled yet.
- **AI Auto-Draft Quote:** describe a shipment → AI extracts line items + required documents; backend computes fees/customs/tax from Fee Calculator rules; draft opens pre-filled → save → one-click watermarked PDF.
- Public site: Hero, stats, dynamic services grid, dynamic service detail pages, about, contact.
- **AI Assistant (pluggable):** OpenAI/Anthropic/Gemini via emergentintegrations. Default Emergent key + admin BYO key in Settings. Public floating chat concierge (fees/docs/services + guides to quote form) and admin ops assistant (streaming).
- **Fee/customs calculator:** rule-based numbers (`/api/calculate`, rates editable in Settings) + AI explains required documents.
- **Quotes & Documents builder:** create quote/receipt/customs docs with line items + auto totals, auto number (EXD-Q-#####), generate watermarked (company logo) PDF → saved to "Send to Client" folder, downloadable.
- **Global search:** clients, quote requests, documents by name/phone/email/date/port/quote no./PO no./tracking no./item.
- Request-a-Quote pipeline (public form → CRM cards → convert to client).
- Visitor tracking + heatmap; CRM (Requests, Clients, Visitors, Documents); Services CRUD + per-service SEO; Object Storage; SEO controls; Settings; Profile.
- **Portability:** `storage.py` supports `STORAGE_BACKEND=local|emergent`; Dockerfiles, docker-compose.yml, .env.example files, and DEPLOYMENT.md for self-hosting outside Emergent.

## Architecture (updated)
- Backend modules: server.py (routes), ai.py (LLM), pdf_utils.py (PDF), storage.py (portable storage).
- AI streams as raw text/plain; frontend reads body stream (lib/chat.js).

## Test Credentials
admin@executivedistribution.com / Executive2025!

## Backlog / Next
- P1: Per-page (non-service) SEO overrides; sitemap.xml + robots.txt generation.
- P1: Client-linked documents in CRM (associate docs to a client).
- P2: Brute-force lockout on login; rate limit /api/track.
- P2: Drag-to-reorder services; multi-user admin roles.
- P2: Split server.py into routers as it grows.
