# Edora frontend

Next.js App Router + React + TypeScript. Python is in the separate FastAPI backend. No Python installation is needed for this project.

## Requirements
- Node.js 22 LTS (22.9+) and npm.
- Backend running at http://localhost:8000 (see its README).

## Start locally — Windows, macOS, Linux
```sh
npm ci
npm run dev
```
Visit http://localhost:3000. Defaults work without an environment file.

For custom settings, copy `.env.example` to `.env.local`:
```sh
# macOS/Linux
cp .env.example .env.local
```
```powershell
# Windows PowerShell
Copy-Item .env.example .env.local
```
Restart Next.js after changes.

| Variable | Default | Purpose |
|---|---|---|
| BACKEND_URL | http://localhost:8000 | Server-only FastAPI origin; no trailing slash |
| APP_ORIGIN | http://localhost:3000 | Exact browser origin accepted for mutations |
| COOKIE_SECURE | false | Set true behind HTTPS in production |

Use `localhost` consistently, not `127.0.0.1`, unless APP_ORIGIN and backend FRONTEND_URL are also changed. Never prefix server secrets with NEXT_PUBLIC_. For a different port use `npm run dev -- --port 3001`, set APP_ORIGIN and the backend FRONTEND_URL to http://localhost:3001.

## Commands
```sh
npm run dev        # development
npm run typecheck  # TypeScript validation
npm run build      # production build
npm start          # run built app on port 3000
```

## Pages
| Route | Page |
|---|---|
| `/` | Home |
| `/about` | About us |
| `/editors` | For editors |
| `/contact` | Contact form |
| `/register` | Editor registration |
| `/login` | Login |
| `/verify-email?token=...` | Explicit email confirmation |
| `/resend-verification` | Request a replacement link |
| `/dashboard` | Protected editor profile |

The header exposes logout after authentication. Backend logout revokes the session before the frontend cookie is removed. Verification requires a button click so email scanners do not activate accounts merely by fetching a URL. The token is removed from the current browser URL after successful verification, and all pages set `Referrer-Policy: no-referrer`.

## Internal API
`src/app/api/[...path]/route.ts` proxies only the documented auth and contact routes. POST requests require the exact APP_ORIGIN Origin header. Tokens remain in HttpOnly, SameSite=Lax cookies; they are never placed in localStorage or returned from the internal login endpoint. FastAPI validates every protected request. Server components call FastAPI directly.

No browser-to-backend CORS configuration is needed because browser requests use the same-origin Next.js internal API.

## Smoke test
1. Start the backend (including Mailpit), then the frontend.
2. Register a unique email with all fields and a 12+ character password.
3. Confirm login is blocked before verification.
4. Open http://localhost:8025, follow the email link, and confirm verification.
5. Log in, inspect `/dashboard`, then log out.
6. Confirm `/dashboard` redirects to login after logout.
7. Submit Contact us; inspect the captured notification in Mailpit.
8. Resend an unverified account's link; its older link must fail.

## Troubleshooting
- Backend unavailable: check http://localhost:8000/health and backend logs.
- Invalid request origin: APP_ORIGIN must exactly match the URL in your address bar.
- Missing email: use Mailpit's web inbox and check backend SMTP configuration.
- Cookie not retained on HTTP: use COOKIE_SECURE=false for localhost only.
- Port occupied: stop the other server or configure a consistent alternate port.

Dependencies are recorded in package-lock.json. Use `npm ci` for reproducible installs. Production hardening items are listed in the root README.


## Website templates

Super admins can create and edit templates at `/admin/templates`, with live previews of header, menu, content, and footer sections. Choose a horizontal, left-sidebar, or right-sidebar menu and use the arrows to reorder sections. Save persists the layout; cancel discards the draft. Two database starter templates are provided: Classic Journal and Sidebar Studio.

Editors can choose and save a template in `/dashboard`. Selections reference the saved template, so later admin edits appear for those users. These are reusable layout configurations and previews; page publishing is not implemented here. Template content is plain text, not executable HTML.

Template requests use internal `/api/admin/templates`, `/api/templates`, and `/api/website/template` routes. The sibling backend's `ADMIN_API.md` documents validation and migration `0003`.


## Admin web pages

At `/admin/pages`, super admins can add, edit, preview, search, and delete database-backed web pages. Enter a title, URL slug, and content using the open-source Tiptap visual editor. Supported controls include headings, bold, italic, underline, lists, quotes, code, links, undo, and redo. Generated HTML can be inspected below the editor. Saving cleans unsupported HTML; deletion requires confirmation. Page previews use a sandboxed iframe. This manages page content; public page publishing is separate.

All page operations use `/api/admin/pages` and `/api/admin/pages/{id}`. See the backend's `ADMIN_API.md` for migration 0004 and endpoint details.
