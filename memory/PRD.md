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
- **Request-a-Quote pipeline:** public form (name*, email*, company, phone, shipping destination, description, up to 4 reference images) → stored as quote-request cards in CRM. Admin can set status (new/reviewing/quoted/closed), delete, and convert a request into a Client.
- Footer admin access is now a small company logo (bottom-right) linking to /login (editable from Settings).
- Visitor tracking: pageview/click/scroll → visitors + events.
- Auth: admin login, protected /admin, profile update + password change.
- Admin dashboard: overview stats incl. New Requests, 14-day traffic chart, top pages, click heatmap.
- Services: full CRUD + per-service SEO + image upload.
- CRM: Quote Requests, Clients CRUD, Visitors list, Documents upload.
- Object Storage: asset upload grid (logo lives here). SEO controls + Settings (all site content).

## Test Credentials
admin@executivedistribution.com / Executive2025!

## Backlog / Next
- P1: Per-page (non-service) SEO overrides; sitemap.xml + robots.txt generation.
- P1: Client-linked documents in CRM (associate docs to a client).
- P2: Brute-force lockout on login; rate limit /api/track.
- P2: Drag-to-reorder services; multi-user admin roles.
- P2: Split server.py into routers as it grows.
