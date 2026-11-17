# Edora frontend

Next.js App Router + React + TypeScript. Python is in the separate FastAPI backend. No Python installation is needed for this project.

## Requirements
- Node.js 22 LTS (22.9+) and npm.
- Backend running at http://localhost:8000 (see its README).

## Start locally Ã¢â‚¬â€ Windows, macOS, Linux
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
`src/app/api/[...path]/route.ts` proxies only the documented auth and contact routes. POST requests require the exact APP_ORIGIN Origin header. Tokens remain in HttpOnly, SameSite=Lax cookies; they are never placed in localStorage or returned from the internal login endpoint. FastAPI validates every protected request. Server components use the internal API for account checks.

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

Editors create their journal at `/dashboard/journal`: choose a template, select admin pages, and name the journal. Creation saves private template and page copies; later admin changes never replace journal content. Editors can edit their copied layout and HTML pages. Public hosting/publishing is not implemented here.

Template requests use internal `/api/admin/templates`, `/api/templates`, and `/api/website/template` routes. The sibling backend's `ADMIN_API.md` documents validation and migration `0003`.


## Admin web pages

At `/admin/pages`, super admins can add, edit, preview, search, and delete database-backed web pages. Enter a title, URL slug, and content using the open-source Tiptap visual editor. Supported controls include headings, bold, italic, underline, lists, quotes, code, links, undo, and redo. Generated HTML can be inspected below the editor. Saving cleans unsupported HTML; deletion requires confirmation. Page previews use a sandboxed iframe. This manages page content; public page publishing is separate.

All page operations use `/api/admin/pages` and `/api/admin/pages/{id}`. See the backend's `ADMIN_API.md` for migration 0004 and endpoint details.


## Editor workspace

Signed-in editors see Profile and Journal in a compact left sidebar. `/dashboard` edits the current account profile. Changing an email signs the editor out and requires verification of the new address; protected account fields cannot be edited.

`/dashboard/journal/new` creates a journal using the template-first wizard and selected admin pages. Copies are stored together in a transaction and remain independent across editors and from the admin library. Edit section colors, layout, and text in the private template editor, or use Tiptap to edit private page HTML. The saved website preview combines the journal layout and copied pages. Page-selection order becomes the website's page order.

All calls use internal `/api/editor/*` routes. Backend migration 0006 and API contracts are documented in `../edora-backend/ADMIN_API.md`.


## Frontend API regression tests

Run `npm test` to check the internal API proxy and browser helper with mocked responses. Coverage includes JSON null for editors without a journal, empty/malformed response errors, validation messages, and bodyless delete responses. Tests make no backend calls and do not modify application data.


### Create private pages during journal setup

In `/dashboard/journal/new`, the Select pages step offers **Create page**. Write a title, unique slug, and rich-text content, then add the page to the journal draft. Edit or remove custom drafts before proceeding. Select admin pages, write new pages, or combine both (up to 100 pages total). Selected admin copies appear first, followed by custom pages.

Click **Create my journal** to persist both copied and new pages together. New pages never enter the admin library or another editor's journal. They can be edited afterward under My pages. Custom drafts are local until journal creation succeeds; refreshing the browser before that discards them.


### Standalone journal previews

After creating a journal, use **Preview journal** to open a separate website in a new tab. URLs use `/<editor-code>/<journal-slug>/<page-slug>`, for example `http://localhost:3000/iut87834/my-journal/home`. Dots after `:3000` would form an invalid port, so local previews use path segments.

Each journal site uses its private saved template, colors, and HTML pages, without the portal header or sidebar. Its navigation includes all pages, Current, and Archives. Current/Archives display existing pages with those slugs, or empty states until issue content is available. Links are publicly readable; editing remains restricted to the journal owner. Inactive or unverified accounts' journals are unavailable. Preview URLs use stable codes and slugs; the backend's migration 0007 backfills existing records.


### Manage My Pages

After journal creation, **My pages Ã¢â€ â€™ Add page** immediately saves a new private page using the visual editor. It appears in the journal menu and never enters the admin library. In each row, change the **Order** number, using each number from 1 through the page count exactly once, then click **Save order**. **Reset order** discards pending ordering changes. Saved order is shared by the dashboard preview and standalone website navigation.

### Journal workspace sections

My Journal uses four on-demand panels: Journal Info (name, website address, dates, and key details), Journal Template (personal design and editor), Journal Pages (private page creation, editing, and ordering), and Preview (saved website preview and external link). Open a section to load its component. Loaded panels retain local drafts while switching sections; full browser refresh still discards unsaved changes. Arrow keys, Home, and End navigate the section tabs.


### Journal collection

The Journal menu opens `/dashboard/journal` with tiles for all of the editor's journals. Click a tile to open `/dashboard/journal/{id}` and its Info, Template, Pages, and Preview sections. Use **All journals** to return, or **Create journal** for `/dashboard/journal/new`. Multiple journals are supported with different URL slugs. All management requests include the selected journal ID. Backend migration 0008 preserves existing content and preview URLs.

### Journal status

Every journal starts as Draft. Tiles and the management banner display Draft, Published, or NotPublished. Open Journal Info, choose a status, and click Save status to update only the selected journal. Preview links remain available in all states. Backend migration 0009 adds the status column, backfills existing journals to Draft, and restricts allowed values.
