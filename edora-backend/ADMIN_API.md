# Super admin and user management

Credentials are in backend `.env`: `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD`. Never add these to the frontend or NEXT_PUBLIC variables.

After deploying code, run `alembic upgrade head` and `python -m app.seed_admin` from the backend directory. Docker: `docker compose up -d --build api` then `docker compose exec api python -m app.seed_admin`. Provisioning is idempotent: existing admins and passwords remain unchanged; an existing editor is never promoted automatically.

Log in through the normal frontend /login page. Super admins go to /admin; editors go to /dashboard.

Browser -> frontend /api/* -> backend /api/v1/*, including server-rendered account checks. The internal API stores the bearer token in an HttpOnly cookie. The backend enforces roles and active status on every authenticated request.

| Backend endpoint | Method | Purpose |
| --- | --- | --- |
| /api/v1/auth/login | POST | Existing login endpoint, also authenticates admin |
| /api/v1/auth/me | GET | Now includes role and is_active |
| /api/v1/admin/users?offset=0&limit=20&search= | GET | Returns {items, total}; limit 1–100 |
| /api/v1/admin/users/{id} | PATCH | Update first_name, last_name, email, phone, gender, is_active (all required) |
| /api/v1/admin/users/{id} | DELETE | Permanently delete user and their sessions/verification tokens |

All admin endpoints require an authenticated active super_admin. Editor registration cannot set roles. Admin accounts are visible but protected from editing/deletion. Passwords/hashes are never returned. Inactivation revokes sessions and prevents login; reactivation does not restore revoked sessions. Changing email revokes sessions and clears verification; the user must request a new verification email. Duplicate email updates return 409. Missing users return 404. Unauthorized access returns 401/403.

Migration 0002 adds role (default editor) and is_active (default true), preserving existing accounts.


## Website templates

Migration `0003` adds `website_templates` (name, description, validated JSON layout, creation/update timestamps) and `website_template_selections` (one selected template per account). It inserts Classic Journal (horizontal menu) and Sidebar Studio (left menu) once; normal restarts do not overwrite edited layouts.

| Backend endpoint | Method | Purpose |
| --- | --- | --- |
| /api/v1/admin/templates | GET | List saved templates; super admin only |
| /api/v1/admin/templates | POST | Create template; super admin only; returns 201 |
| /api/v1/admin/templates/{id} | PATCH | Replace editable template fields; super admin only |
| /api/v1/templates | GET | List templates available to authenticated users |
| /api/v1/website/template | GET | Read current account selection, or null |
| /api/v1/website/template | POST | Save current account selection using {"template_id": 1} |

Create/edit body: `name` (1–100 characters), `description` (up to 500), and `layout`. Layout contains `menu_position` (`top`, `left`, or `right`) and an ordered `sections` array with exactly one each of `header`, `menu`, `content`, and `footer`. Every section has `type`, `title` (1–100 characters), and `content` (up to 2000 characters). Menu content uses one item per line. Unexpected fields, invalid placement, duplicate/missing sections, and blank names/titles return 422. Duplicate template names return 409; missing template IDs return 404.

The preview renders plain text, without executing template HTML or scripts. Horizontal layouts follow section order; sidebar menus appear beside the content while other sections span the width. User selections reference live templates, so admin changes also update selected layouts. This provides layout configuration and previews; page publishing and menu destinations are separate features.

Deploy with `docker compose up -d --build api` (startup applies migrations). All frontend requests use matching internal `/api/*` routes, which forward to these backend endpoints.


### Section colors

Every section accepts optional `background_color` and `text_color` fields as six-digit hexadecimal values (for example, `#244c40`). The API normalizes colors to lowercase and rejects invalid values with 422. Omitted/null fields use section-specific defaults, preserving existing template appearances. Colors are stored in the existing layout JSON when a template is saved; no database migration or new endpoint is required. Admin, library, and selected-template responses include resolved colors. Frontend editing provides color pickers, hex inputs, live previews, and per-section color resets.


### Delete a template

`DELETE /api/v1/admin/templates/{id}` requires an active super-admin session. The frontend calls internal `DELETE /api/admin/templates/{id}` after confirmation. Success returns 204 without a body; missing templates return 404. Templates selected by any account cannot be deleted (409); users must first select another template. Template selection and deletion lock the template row to serialize concurrent changes, and database foreign keys also protect references. No migration is required. Starter templates can be deleted when unused and will not be recreated on restart.


## Web pages

Migration `0004` creates `web_pages`: id, title (150 characters), unique slug (150 characters), content_html (TEXT), created_at, and updated_at.

All endpoints require an active super-admin session:

| Backend endpoint | Method | Purpose |
| --- | --- | --- |
| /api/v1/admin/pages | GET | List page summaries without content |
| /api/v1/admin/pages | POST | Create a page (201) |
| /api/v1/admin/pages/{id} | GET | Fetch page HTML for editing/preview |
| /api/v1/admin/pages/{id} | PATCH | Update title, slug, and content_html |
| /api/v1/admin/pages/{id} | DELETE | Permanently delete a page (204) |

Create/edit requires `title`, `slug`, and `content_html`. Slugs use lowercase letters/numbers with single hyphens (example: `about-us`); duplicate slugs return 409. Missing IDs return 404. HTML is limited to 100,000 characters; empty text after sanitization returns 422. `nh3` sanitizes HTML before storage, preserving headings, paragraphs, formatting, lists, code, quotes, and safe links while removing scripts, event handlers, embeds, and unapproved tags/attributes. Pages are managed content records; public routing/publishing is not enabled by this change.

The frontend uses Tiptap's MIT-licensed open-source editor and sandboxed HTML previews. All calls use internal `/api/admin/pages` routes first. The internal proxy allows page bodies up to 650,000 UTF-8 bytes (including JSON escaping); other endpoints retain their 20,000-byte limit. Deploy using `docker compose up -d --build api` to install nh3 and apply migration 0004.


## Journal content seeds (migration 0005)

`0005_seed_journal_pages.py` inserts Home (`home`), About the Journal (`about-the-journal`), Editorial Team (`editorial-team`), and Submissions (`submissions`) into `web_pages`. HTML was rewritten from the corresponding eelet.org.uk pages reviewed on 15 November 2026; source links are included in each page. The migration contains static content and makes no network requests. No API or schema changes are required.

Existing matching slugs are skipped, preserving their title, HTML, and timestamps. Repeated execution is safe. Downgrade intentionally retains all pages to protect editorial changes; it does not remove seed content. Apply with `alembic upgrade head`, or rebuild/start the Docker API. Edit the seeded content under Admin â†’ Pages afterward.

Content decisions: the source homepage conflicts on publication frequency, so no frequency is asserted there. The editorial directory repeats Muhammad Umar Riaz Abbasi; the seed lists him once. No unverified preservation-service implementation or specific Creative Commons license is asserted. Source links point to the original journal, including its submission system; this migration does not implement local manuscript submissions.


## Editor workspace and independent journals

Migration `0006` creates `editor_journals` (owned by an editor, with journal name and complete template name/description/layout copies) and `editor_journal_pages` (independent title/slug/HTML copies, position and timestamps). Journal page slugs are unique within each journal, not globally. These tables reference the owning editor/journal only: no foreign keys or live reads link them to master templates or pages. Deleting an editor removes their journal and copies without affecting other accounts.

| Backend endpoint | Method | Purpose |
| --- | --- | --- |
| /api/v1/editor/profile | PATCH | Update own first_name, last_name, phone, gender, email |
| /api/v1/editor/pages | GET | Read admin page library summaries |
| /api/v1/editor/pages/{id} | GET | Read an admin source page |
| /api/v1/editor/journal | GET | Own journal with copied layout and pages, or null |
| /api/v1/editor/journal | POST | Atomically create private template/page copies |
| /api/v1/editor/journal/template | PATCH | Edit own copied template using TemplateInput |
| /api/v1/editor/journal/pages/{id} | PATCH | Edit own copied page using PageInput |

All endpoints require an active verified editor account. No client-supplied owner ID is accepted. Copied-page lookups are scoped to the signed-in editor's journal; other editors' page IDs return 404. Admin accounts cannot use editor mutation endpoints. HTML sanitation and color validation are reused from admin schemas.

Create body: `name` (1â€“150 characters), `template_id`, and distinct `page_ids` (1â€“100). Pages are copied in selection order. Creation locks the editor and source rows, validates all selections, and commits the journal and pages in a single transaction. Missing sources return 404 without partial records; repeat creation returns 409. Admin edits/deletions after creation never update or remove existing journal copies. Copy edits never update masters or other journals. The older `/website/template` selection remains a separate legacy selection and is not a journal; dashboard creation requires explicit selection and confirmation.

Profile email changes revoke sessions, clear verification, and send a new verification link. Duplicate email updates return 409. Role, verification, active status, passwords, and ownership cannot be changed through profile payloads.

Use `docker compose up -d --build api` to apply migration 0006. Frontend uses internal `/api/editor/*` routes only. Editor dashboard Profile is `/dashboard`; Journal is `/dashboard/journal`. The website preview shows saved private content in a sandbox. Public website hosting/publishing, additional journals per editor, and adding pages after initial creation are not implemented by this change.


### Editor-authored pages during journal creation

`POST /api/v1/editor/journal` now accepts optional `new_pages`, an array of `{title, slug, content_html}` validated and sanitized with the same rules as page editing. `page_ids` is optional; include at least one page across both arrays, up to 100 total. Selected admin pages are copied first in selection order, followed by new pages in array order. New pages are written only to the authenticated editor's `editor_journal_pages`, never to `web_pages` or another editor's journal.

Duplicate custom slugs return 422; custom slugs conflicting with selected admin pages return 409. Combined new-page HTML is limited to 1,000,000 characters, with a 100,000-character limit per page. Creation remains atomic; failed validation leaves no partial journal. Frontend internal POST `/api/editor/journal` allows 6,500,000 UTF-8 bytes to accommodate JSON escaping; other existing route limits are unchanged. No migration is required.

The Select pages step allows editors to write, edit, and remove local custom-page drafts with Tiptap. Drafts are persisted when Create my journal succeeds, and can then be edited like other private journal pages. Browser refresh before journal creation discards unsaved drafts.


## Standalone journal preview websites

Migration `0007` adds unique eight-character lowercase alphanumeric `editors.public_code` values and stable `editor_journals.slug` values, including backfills for existing accounts/journals. New accounts receive codes automatically; new journals derive a slug from the name. Non-ASCII-only names fall back to `journal`. The editor code separates journals belonging to different accounts even when their names match.

Editor journal responses now include `editor_code`, `slug`, and `preview_path`. The preview link opens a standalone journal website at `/{editor_code}/{journal_slug}/{page_slug}` (for example, `http://localhost:3000/iut87834/my-journal/home`). Text after a URL port is invalid, so the requested dotted `localhost:3000.code.journal.page` example is represented using valid URL path segments. This does not require DNS or subdomain configuration.

Public read-only endpoint: `GET /api/v1/public/journals/{editor_code}/{journal_slug}`, reached through internal `/api/public/journals/...`. It returns only journal name, slug, code, copied template layout, and copied page titles/slugs/sanitized HTML. It never returns account email, credentials, owner IDs, or edit permissions. Only active, verified editor accounts are available; absent/disabled journals return 404. Preview URLs are shareable and do not require login; the editor code is an identifier, not a password. Edit operations still require the owning editor's session.

The standalone frontend omits portal navigation, renders saved colors and section placement, and creates links for all copied/new pages plus Current and Archives. If the journal already has a page using either slug, that page's content is shown without duplicate menu items. Otherwise those pages show truthful empty states; issue publishing is not implemented. Uppercase page-slug requests redirect to lowercase. Unknown pages return 404. Preview metadata requests search engines not to index the site. Data is fetched without caching so saved changes appear on refresh.

Apply with `docker compose up -d --build api` or `alembic upgrade head`.


## Manage pages after journal creation

- `POST /api/v1/editor/journal/pages`: append a private page using `{title, slug, content_html}`; returns the updated journal with status 201. Reuses HTML sanitization. Duplicate slugs or a 100-page journal return 409. Only `editor_journal_pages` is written; the admin `web_pages` library is never changed.
- `PATCH /api/v1/editor/journal/pages/order`: accept `{page_ids: [3, 1, 2]}` listing every page in the current editor's journal exactly once, in the desired order. Returns the updated journal. Duplicate/invalid IDs return 422; missing or foreign IDs return 409. Changes are atomic and update the existing position column.

Both operations require the owning editor's authenticated session. The journal row is locked to serialize page mutations. Current journal reads, previews, and public website menus use the saved order. No schema migration is needed. Frontend calls only internal `/api/editor/journal/pages` and `/api/editor/journal/pages/order`. Single-page creation uses the same 650,000-byte proxy limit as page editing.


## Multiple journals and tile navigation (migration 0008)

Migration 0008 removes the one-journal-per-editor constraint and adds unique `(editor_id, slug)` plus an owner index. Existing content and preview URLs are preserved. Downgrade refuses when an editor owns multiple journals, without deleting records.

`GET /api/v1/editor/journals` returns the signed-in editor's tile summaries: id, name, slug, template_name, page_count, created_at, updated_at. Full page HTML is not included.

Read and mutation endpoints under `/editor/journal` accept `?journal_id={id}`. Ownership is checked on every request; a foreign journal returns 404. Page IDs must belong to that selected journal even when an editor owns both journals. Legacy calls without a journal ID work for a single journal; multiple journals return 409 requiring explicit selection. Creation permits multiple journals; duplicate name-derived slugs for the same editor return 409. The internal frontend proxy forwards query parameters.

Frontend routes: `/dashboard/journal` lists tiles, `/dashboard/journal/new` creates a journal, and `/dashboard/journal/{id}` opens its management screen. Apply with `alembic upgrade head` or `docker compose up -d --build api`.


## Journal status (migration 0009)

Each journal has `status`, restricted to `Draft`, `Published`, or `NotPublished`. Migration 0009 adds a non-null column with a database default of Draft and a check constraint. Existing journals are backfilled to Draft; newly created journals always start as Draft (creation does not accept status overrides). Tile summaries and full management responses include status.

`PATCH /api/v1/editor/journal/status?journal_id={id}` accepts only `{"status":"Published"}` (or either other allowed value) and returns the updated journal. Only the owning editor can change status; other owners receive 404 and unauthenticated callers receive 401. Invalid status values or unexpected fields return 422. The selected journal is locked and its updated_at timestamp is refreshed. Other journals are untouched.

The frontend uses internal `/api/editor/journal/status?journal_id={id}`, displays badges on tiles and in the workspace, and offers a selector with Save status in Journal Info. Status tracks journal workflow; shareable preview access remains unchanged in every state. Apply with `alembic upgrade head` or rebuild/start the Docker API.
