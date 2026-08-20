# Executive Distribution

Private FastAPI + MongoDB + React site for an import/export and product-sourcing company. The repo is a single app with a public marketing site and a JWT-gated admin CRM.

This is not a hosted production URL. Self-hosting, Docker, nginx, and environment details live in [`DEPLOYMENT.md`](DEPLOYMENT.md).

## Public site vs admin

**Public (no login)**

- Home, service cards, and service detail pages (copy and SEO driven from the admin dashboard)
- Request-a-quote form (creates a CRM quote request)
- Optional AI concierge chat (fees/docs/services) when an AI provider is configured
- Tokenized client portal (`/portal/:token`) to view shared documents and approve a quote
- Visitor tracking / heatmap events (`POST /api/track`)

**Admin (`/login` → `/admin`)**

JWT email/password. Superadmin is seeded on first backend start from `ADMIN_EMAIL` / `ADMIN_PASSWORD`. Sub-admins get section permissions (dashboard, CRM, SEO, research, storage, and so on).

- Dashboard, analytics, heatmap, backups, GitHub update checker
- CRM: quote requests, clients, visitors, documents, bulk actions, CSV export
- Quotes and document builder (line items, PDFs, client share links)
- Services CRUD and per-service SEO
- Site-wide SEO controls, sitemap/robots generators
- Research scraper (keywords + URLs → contacts that can be imported as CRM leads)
- Object storage, settings, profile, team/RBAC, audit log, AI ops assistant

## CRM, quotes, SEO, research (high level)

| Area | What it does |
| --- | --- |
| CRM | Clients, quote-request pipeline, visitor sessions, documents, tags/lead score, bulk update/delete |
| Quotes | Public intake → admin cards → convert to client; document/PDF generation; portal approval |
| SEO | Global + per-page meta, canonical site URL, generated `/api/sitemap.xml` and `/api/robots.txt`. Optional IndexNow ping when a key is set in Settings |
| Research | Admin-only scrape of supplied URLs (title, text, emails, phones, keyword hits). Optional JS rendering via ScraperAPI. Contacts can be saved into CRM |

## Integrations (honest status)

These are **not** all live just because fields exist.

- **Email (Resend/SendGrid):** provider, from-address, and API key are stored in Settings. Sending is **not wired**.
- **Research JS render:** needs a ScraperAPI key in **Settings** (write-only). Without it, the scraper uses plain HTTP + BeautifulSoup.
- **Slack:** webhook stored in Settings; used for backup/approval alerts when enabled.
- **Social login (Stytch/Stitch):** credentials can be saved; login is **not wired**.
- **AI:** Emergent universal key (`EMERGENT_LLM_KEY`) only works on Emergent. Self-host: add your own OpenAI / Anthropic / Gemini key in Settings → AI Assistant.
- **CORS:** `DEPLOYMENT.md` documents `CORS_ORIGINS`. The API currently allows all origins (`allow_origins=["*"]`, credentials off). Restrict that before exposing a public host.
- **Backups:** zip of Mongo collections (+ optional uploads) to a local folder. S3/Drive destinations are not implemented.

## Run locally (Mongo + uvicorn + yarn)

You need Python 3.11+, Node/Yarn, and a MongoDB instance (`mongod`, Docker, or Atlas).

1. Copy env templates (names only; fill in values locally — never commit `.env`):

   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

   Set at least `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` in `backend/.env`, and `REACT_APP_BACKEND_URL` in `frontend/.env` (local API origin, no `/api` suffix).

2. MongoDB listening where `MONGO_URL` points (compose Mongo is `mongodb://localhost:27017` if you only run the `mongo` service).

3. Backend:

   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
   uvicorn server:app --host 0.0.0.0 --port 8001
   ```

   API: http://localhost:8001/api  
   First start seeds the admin user, default services, and site settings.

4. Frontend (dev):

   ```bash
   cd frontend
   yarn install
   yarn start
   ```

   Web: http://localhost:3000  
   Admin: http://localhost:3000/login (use `ADMIN_EMAIL` / `ADMIN_PASSWORD`)

## Docker Compose

```bash
cp backend/.env.example backend/.env   # fill JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD, DB_NAME, …
docker compose up --build
```

Compose starts Mongo, the API on port 8001, and the frontend on port 3000. It sets `MONGO_URL` and local file storage for the backend container. Optional nginx (single origin, `/sitemap.xml` and `/robots.txt` at the site root) is commented in `docker-compose.yml`; config is [`deploy/nginx.conf`](deploy/nginx.conf).

## Self-host / deploy

Use **[`DEPLOYMENT.md`](DEPLOYMENT.md)** — Docker, non-Docker, storage (`STORAGE_BACKEND`), AI keys, nginx rewrites, and a go-live checklist. [`deploy/update.sh`](deploy/update.sh) is a code-only update helper; point `UPDATE_SCRIPT` at it on self-hosted boxes if you want the admin “Apply update” button.

This repository does not define a production hostname or managed cloud target.

## Environment files

| File | Used by |
| --- | --- |
| [`backend/.env.example`](backend/.env.example) | FastAPI (`backend/.env` via docker-compose `env_file`) |
| [`frontend/.env.example`](frontend/.env.example) | CRA/craco (`REACT_APP_BACKEND_URL` is baked in at build time) |

Templates list **variable names only**. Slack, email, ScraperAPI, and IndexNow keys live in the Settings document in Mongo, not in `.env`.

`.gitignore` ignores `.env`, `.env.*`, and `*.env`, and **keeps** `.env.example`.
