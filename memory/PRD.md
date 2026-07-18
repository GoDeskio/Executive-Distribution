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
