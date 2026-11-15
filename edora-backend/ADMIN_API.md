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
