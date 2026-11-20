# Publishing Journal Websites to Subdomains

## 1. Goal and current behavior

Add a **Publish** action under **Admin → Editor → Journal**. An administrator chooses a subdomain, publishes a journal, and receives its public website URL.

Example:

- Portal: `https://portal.example.com`
- Journal: `https://my-journal-iut87834.journals.example.com`
- Journal page: `https://my-journal-iut87834.journals.example.com/about-the-journal`

Replace `example.com` with your actual domain. The hostname before `journals.example.com` is one DNS label. A URL such as `localhost:3000.code.journal.page` is invalid; the port belongs after the hostname.

**This document is an implementation and deployment guide. Subdomain publication is not implemented yet.** Current preview URLs use `/<editor-code>/<journal-slug>/<page-slug>`. Existing `Published` status is an editor-controlled workflow label; it does not provision DNS, issue a certificate, or deploy a website. Current previews also show saved editor changes immediately, regardless of that status.

The recommended design runs all journal sites on the existing application. Publishing adds a hostname mapping and a content snapshot; it does not create a new container for every journal.

## 2. Choose the publication rules

Before implementation, establish these rules:

1. Only a super admin can publish, republish, or unpublish a website.
2. Each journal initially has one public subdomain.
3. A publication contains a snapshot of the journal's personal template and ordered page copies. Never publish the shared admin template/page records directly.
4. Subsequent editor changes stay in the journal workspace until an admin republishes.
5. Draft previews remain separate from the published site. A publication must not become live solely because an editor selects `Published` in Journal Info.
6. Unpublishing immediately disables the public hostname, without deleting journal content.
7. Current and Archives use saved pages with those slugs, or the existing empty states. Publishing does not implement issue/article management.

Record whether disabling an editor also disables their published sites. Recommended: deny public access while the owner is inactive/unverified, including when serving a snapshot.

## 3. Prepare the domain, server, and DNS

You need:

- Control of a registered domain and its DNS records.
- A production host for Next.js, FastAPI, and PostgreSQL.
- An HTTPS reverse proxy/load balancer and persistent certificate storage.
- Production secrets, database backups, and working SMTP.

Create these records in your DNS provider:

| Record | Example name | Value |
| --- | --- | --- |
| A | `portal.example.com` | Public server IPv4 address |
| A | `*.journals.example.com` | Public server IPv4 address |
| A | `journals.example.com` | Same address, only if the base hostname will be served |

Use AAAA only if the server actually serves IPv6. A wildcard CNAME to the hosting provider's target can replace the wildcard A record when that provider requires it. Do not configure both A and CNAME for the same name.

The wildcard means new journals do not need individual DNS changes. The application still must reject unregistered hostnames. A wildcard certificate for `*.journals.example.com` covers one label, not `code.name.journals.example.com`.

For managed hosting, register both the portal and wildcard journal domain with that platform and follow its verification steps. Select either managed hosting or self-hosting; do not mix their routing instructions unintentionally.

## 4. Configure HTTPS and the reverse proxy

For self-hosting, put Caddy or Nginx in front of Next.js. Keep Next.js and FastAPI application ports private. The proxy must preserve the original host and send the correct forwarded protocol. Trust forwarded headers only from your own proxy.

Caddy example, **assuming Cloudflare DNS and a Caddy binary containing its DNS provider module**:

```caddyfile
portal.example.com {
    reverse_proxy 127.0.0.1:3000
}

*.journals.example.com {
    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }
    reverse_proxy 127.0.0.1:3000
}
```

This is a provider-specific example, not a drop-in file for every DNS provider. Install/build Caddy with the matching provider module, configure a narrowly scoped DNS token through the service environment, and persist Caddy's certificate data. Wildcard certificates require DNS validation; a standard Caddy image without that module is insufficient for this example.

If the proxy runs in Docker, `127.0.0.1` refers to that container. Use the frontend service's private network address instead. Expose ports 80/443 as required by your chosen proxy/certificate configuration. Validate configuration before reloading it and verify automatic certificate renewal.

References: [Next.js self-hosting](https://nextjs.org/docs/app/guides/self-hosting), [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https), and [Caddy DNS challenge configuration](https://caddyserver.com/docs/caddyfile/directives/tls).

## 5. Configure the production frontend

Existing frontend environment values should point to production services:

```dotenv
BACKEND_URL=http://backend:8000
APP_ORIGIN=https://portal.example.com
COOKIE_SECURE=true
```

`backend` is an example private service hostname; use the actual host/service name. Proposed additional variables, which need code support:

```dotenv
JOURNAL_BASE_DOMAIN=journals.example.com
INTERNAL_APP_ORIGIN=http://frontend:3000
```

`INTERNAL_APP_ORIGIN` should identify this Next.js service on its private network. Public website server rendering can call its internal API there, avoiding a round trip through external DNS. It must never be derived from an untrusted Host header.

Keep admin cookies host-only; do not share them across `.example.com`. Administrative mutations remain restricted to the portal's configured `APP_ORIGIN`. Journal subdomains serve public reads and must not expose portal login/admin mutation routes.

The current Compose file is a local development setup. Add a production frontend service/process, use production PostgreSQL credentials, replace Mailpit with actual SMTP, and update the backend's `FRONTEND_URL` to the portal origin. Do not expose the local database or mail-testing ports publicly.

## 6. Add hostname-aware frontend routing

Implement Next.js hostname routing in `src/proxy.ts`, following the installed Next.js version's Proxy convention:

1. Normalize the hostname: lowercase it, remove the port, and validate it against the configured journal base domain.
2. Treat the portal hostname as portal traffic. Keep existing dashboard and admin routes there.
3. For an allowed journal hostname, rewrite `/` and page paths to a dedicated published-site renderer, for example `/published/{hostname}/{page-slug}`. Preserve the browser's subdomain URL.
4. Handle `/_next/*` and other required static assets separately so they are not rewritten into journal pages.
5. Resolve the host to a live publication using the internal API. Unknown, failed, or unpublished hostnames return 404; never fall back to an arbitrary editor's site.
6. Return the published homepage at `/`, preferring the `home` slug and otherwise the first ordered page. Unknown pages return 404.
7. Generate menus as same-host links such as `/about-the-journal`, `/current`, and `/archives`. Do not reuse preview links containing editor-code/journal-slug prefixes.
8. Render only the journal website; keep portal header/sidebar/footer out of published routes. `PortalChrome.tsx` currently recognizes preview paths only and needs updating.
9. Keep HTML sanitization and validated section colors. Set canonical URLs to the published domain. Published sites may be indexable; draft previews should remain noindex.

Preserve this architecture for all publication reads and mutations:

```text
Browser / server-rendered page
    → Next.js internal /api/*
    → private FastAPI /api/v1/*
    → PostgreSQL
```

Do not call FastAPI directly from a frontend page or component.

Reference: [Next.js Proxy](https://nextjs.org/docs/app/getting-started/proxy).

## 7. Add the admin Publish interface

Under **Admin → Editor → Journal**, add:

- **Publish** for a journal that has no live publication.
- A dialog showing journal/editor details and a proposed subdomain.
- A validated, editable single-label subdomain, a readiness result, and a final Publish action.
- Separate publication state: Publishing, Live, Failed, or Unpublished.
- The live URL plus **Open website**, **Republish**, and **Unpublish** controls.
- Clear failure messages; do not show Live until the publication is committed and reachable.

Suggested label: `my-journal-iut87834`. DNS labels must be 1–63 characters, using lowercase letters, digits, and interior hyphens. Journal slugs can currently exceed that length, so generate a shortened proposal and check uniqueness rather than concatenating values blindly. Reject reserved labels and require another label on collision. Keep a published hostname stable when a journal name changes.

Keep the editor's workflow status distinct from administrator-approved publication state. Display both where relevant. Republish should explicitly replace the live snapshot with the latest approved journal content.

## 8. Test, deploy, and verify

Implement automated checks before production deployment:

- Authentication and super-admin authorization for publishing actions.
- Unique hostname validation, concurrent publish requests, and idempotent retries.
- Correct journal/hostname isolation and exclusion of admin originals.
- Published snapshot remains unchanged after editor edits; republish updates it.
- Unpublish, disabled owners, unknown hosts, and unknown pages deny public access.
- Correct template, colors, page order, menu links, Current, and Archives.
- HTTPS, cookie scope, portal mutation origin checks, and no secret/owner-profile leakage.
- Cache isolation by hostname and release; purge/invalidate on republish or unpublish. Initially prefer no-store for publication resolution so unpublished sites disappear immediately.

Use a staging domain first. For local hostname testing, map a test journal hostname to `127.0.0.1` in the hosts file and use `http://journal-code.journals.test:3000`. A hosts file does not support wildcard entries. Configure the local journal base domain accordingly.

Run frontend `npm ci`, `npm test`, and `npm run build`; run the backend suite against its temporary test database. Back up production PostgreSQL before applying the new migration. Then deploy backend migration/API changes, deploy frontend routing/UI changes, configure DNS/HTTPS, and publish one test journal from the admin portal.

Verify:

```sh
nslookup my-journal-iut87834.journals.example.com
curl -I https://my-journal-iut87834.journals.example.com/
curl -I https://my-journal-iut87834.journals.example.com/current
```

Also open every page in a browser, make an editor-only content change, confirm live content stays unchanged, republish, and confirm it updates. Unpublish and verify the hostname stops serving journal content. Retain old releases so a failed release can be rolled back by atomically restoring the previous active release.

## 9. Required backend changes

The following are proposed changes, not existing APIs or tables.

### Database migration

Add publication records and versioned snapshots, for example:

- `journal_publications`: ID, journal ID, unique normalized hostname, publication state, active release ID, publishing admin ID, timestamps, and a safe failure reason.
- `journal_publication_releases`: ID, publication ID, version, immutable snapshot JSON, creation timestamp, and approving admin ID.
- A unique publication per journal initially; unique release version per publication.
- Snapshot data containing journal name, copied template layout/colors, ordered page titles/slugs/sanitized HTML, and menu configuration. Do not include passwords, sessions, or private profile data.

Define foreign-key behavior and update editor/journal deletion cleanup. Avoid leaving a hostname serving content after its owner or journal is deleted. Add audit records for publish, republish, failure, unpublish, and rollback. Keep the existing Draft/Published/NotPublished workflow column; do not use it as the sole public-access gate.

### Admin APIs

Implement super-admin-only endpoints, with internal frontend counterparts:

| Proposed backend endpoint | Purpose |
| --- | --- |
| `POST /api/v1/admin/editor-journals/{id}/publish` | Validate/reserve hostname and publish an approved snapshot |
| `POST /api/v1/admin/editor-journals/{id}/republish` | Create a new release and switch the live snapshot |
| `POST /api/v1/admin/editor-journals/{id}/unpublish` | Disable public serving without removing editor content |
| `GET /api/v1/admin/editor-journals/{id}/publication` | Return publication state, live URL, and safe error details |
| `GET /api/v1/public/sites/{hostname}` | Return only the active published snapshot for an allowed hostname |

Validate hostnames against a server-configured base domain; never accept arbitrary domains or provisioning URLs. Use transactions and row locks to reserve unique hostnames and create consistent snapshots. Repeated requests must not create duplicate publications. If external provisioning is needed, use a durable background job/outbox with retries and update state separately. Do not hold database locks while waiting for DNS or certificate issuance.

The wildcard model normally avoids DNS API calls during Publish: DNS and certificates are configured once, then publication becomes an application mapping/snapshot operation. Return Live only after a controlled health check confirms the resolved site/release. Keep any health-check target restricted to the validated hostname/base domain.

The public-site endpoint must check live publication state and owner eligibility before returning a snapshot. Keep owner-only journal mutation APIs separate. Add GET/POST paths to `src/app/api/[...path]/route.ts` explicitly; retain authentication forwarding, portal origin validation, body limits, and no-store headers. Public hostname resolution must not reveal private journal content unless a live publication permits it.

Finally, decide how existing publicly readable draft-preview APIs should work in production: keep them as intentionally shareable previews, or protect them with owner/admin authentication or expiring preview tokens. Do not accidentally serve draft data from the published-host renderer.
