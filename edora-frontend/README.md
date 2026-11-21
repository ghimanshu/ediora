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


### Inspect editor templates as admin

Admin → **Editor templates** lists editors' personal journal templates. Filter by editor and journal creation date (inclusive UTC dates), apply or clear filters, and navigate paginated results. **Open journal** opens a read-only inspection screen in a new tab. View the saved template, select pages, and inspect journal content without editing or changing its status. Inactive editor journals remain available to super admins. All inspection requests pass through GET-only internal admin APIs.


### Download a journal as a website

In **Admin → Editor → Journal**, journals marked **Published** have a **Download Website** action. Extract the downloaded ZIP, open its journal folder, then open `index.html`. The folder includes saved page HTML, the personal template's colors/layout, local CSS, and relative menu links, including Current and Archives. No server is needed for local browsing. Upload the folder contents to a subdomain's document root for static hosting. Downloads are snapshots and require another export to include later changes. External reference links still require internet access.


### Live exported Current and Archives pages

Download a fresh website ZIP after deploying this feature. Its Current and Archives pages load published issues/articles using JavaScript through `/api/journal/current` and `/api/journal/archives`. Every request supplies `editor_code` and `journal_slug`; the backend resolves both before returning public data.

`assets/journal-config.js` contains the frontend API origin and journal identifiers. Production exports use backend FRONTEND_URL, which must be your frontend HTTPS origin; adjust api_origin in the extracted config when needed. These two pages require an internet connection and the web application to be running, including when opened from file://. Other pages retain offline navigation and styling. Cross-origin read access is enabled only on the two public feed routes; no login tokens are included.

Current shows the latest published issue; Archives lists earlier issues with pagination. Only published articles are shown. Empty feeds display clear empty states; failures provide Retry. Backend migration 0010 supplies issue/article storage, but issue/article entry and publishing screens are not implemented by this change.


### Articles and Volumes

The editor sidebar includes **Articles** and **Volumes**. Both list all of the editor’s records by default, with optional journal and creation-date filters. In Articles, create/edit a heading, one author name per line, an optional abstract, and a PDF up to 10 MB. Editing can retain or replace the PDF. Owner PDF downloads remain private until publication conditions are met.

In Volumes, create a volume and select multiple available articles. Each article belongs to one volume at most. Remove it from its old volume before moving it; deleting a volume retains its articles as unassigned. Deleting an article removes its PDF too. Article selection order controls order within the volume.

Published volumes and published articles appear in Current/Archives when their journal is also Published and their publication date is not in the future. Uploaded PDFs are linked through the public frontend PDF API, which verifies journal/editor scope. PDFs are persisted in the backend database; migration 0011 preserves existing article metadata and backfills journal ownership.


### Filter Articles and Volumes

Both screens default to **All journals**. Use **Filter by journal**, **Created from**, and **Created to** (inclusive UTC dates), then **Apply filters**. **Clear** restores all records. Lists display the journal and creation date for each row.

Choose exactly one journal when creating an article or volume. That journal is fixed on edits. Volume article selection includes only articles from its own journal. Backend migration 0012 adds creation dates to volumes; existing volume dates use migration time because historical creation dates were not stored.
