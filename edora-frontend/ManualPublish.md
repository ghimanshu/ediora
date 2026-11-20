# Manual Journal Publishing to a Subdomain

## 1. What this guide provides

An editor sets their journal status to **Published**. The administrator reviews it, manually creates a DNS subdomain, and manually configures the web server to serve that journal there.

This guide uses **Caddy on a Linux production server** for HTTPS and reverse proxying. It does not require a Publish button, wildcard DNS, DNS API integration, or a separate application/container for each journal.

**No publishing infrastructure or application changes are executed by this document.** Replace every example domain, IP address, editor code, journal slug, and server path before using the commands.

### Two URL choices

| Method | Example | Application changes |
| --- | --- | --- |
| A: Current application, manual configuration | `https://research.example.com/d6eb698t/my-first-journal/home` | None for hostname routing |
| B: Clean page URLs | `https://research.example.com/home` | Host-aware routing and link generation required |

**Method A is the immediately usable manual approach.** DNS alone cannot select a journal: the Caddy configuration below restricts the subdomain to one journal's existing route.

The current editor status is a workflow label, not a deployment switch. Changing it does not create DNS records, change Caddy, or automatically take a website online/offline. The admin must perform the corresponding manual steps.

## 2. Collect the journal's exact details

1. Ask the editor to finish and save their template, pages, colors, and menu order.
2. The editor opens **Journal Info** and saves the status **Published**.
3. The admin opens **Admin → Editor → Journal** and finds that journal. Confirm the status badge says Published.
4. Click **Open journal** and review its content, all page links, Current, and Archives.
5. Copy the exact preview URL. For example:

   ```text
   https://portal.example.com/d6eb698t/my-first-journal/home
   ```

6. Record:

   | Item | Example |
   | --- | --- |
   | Journal ID | `12` — obtain from the admin journal record/API if needed |
   | Editor code | `d6eb698t` |
   | Journal slug | `my-first-journal` |
   | Homepage slug | `home` |
   | Journal route prefix | `/d6eb698t/my-first-journal` |
   | Requested public hostname | `research.example.com` |

7. Use the homepage actually present in the preview URL. If there is no `home` page, use its first saved page, such as `about-the-journal`.
8. Confirm that the editor account is active and verified. The current public journal API denies access otherwise.

Different journals belonging to the same editor share an editor code but have different journal slugs. Configure the exact code-and-slug combination for each hostname.

## 3. Prepare the production application once

Skip this section only when the portal and journal previews already work over HTTPS on your production server.

1. Provision a server and a domain you control. Keep ports 80/443 available for the HTTPS proxy; keep the application/database ports private.
2. Deploy both repositories, for example under `/srv/edora/edora-frontend` and `/srv/edora/edora-backend`.
3. Configure production PostgreSQL credentials, persistent storage, backups, and real SMTP. The checked-in backend Compose file contains development database/mail settings; adapt those before production use.
4. Apply backend migrations through the existing deployment process (`alembic upgrade head`, or the API container's migration/start command).
5. Configure frontend `.env.local`:

   ```dotenv
   BACKEND_URL=http://127.0.0.1:8000
   APP_ORIGIN=https://portal.example.com
   COOKIE_SECURE=true
   ```

   This example assumes Next.js and FastAPI are reachable from the same host, with FastAPI bound/published only on loopback. If using Docker services, use their actual private service hostnames instead of loopback.

6. Configure backend `FRONTEND_URL=https://portal.example.com` so verification emails point to the portal, not a journal subdomain.
7. Build and start the frontend:

   ```sh
   cd /srv/edora/edora-frontend
   npm ci
   npm test
   npm run build
   npm start -- --hostname 127.0.0.1 --port 3000
   ```

   Use a production process supervisor, such as systemd or your container platform, to keep Next.js running after logout/reboot. The last command is a foreground startup example, not service installation.

8. Install Caddy using the instructions for your server OS, persist its certificate storage, and configure the portal:

   ```caddyfile
   portal.example.com {
       reverse_proxy 127.0.0.1:3000
   }
   ```

9. Point `portal.example.com` to the server in DNS, start Caddy, and verify login, journal creation, and preview routes through the portal.
10. Keep admin session cookies host-only. Do not set a parent-domain cookie for `.example.com`.

The application must continue to use this flow:

```text
Journal page → Next.js internal /api/* → private FastAPI → PostgreSQL
```

`src/lib/public-journal.ts` currently calls the internal API at `APP_ORIGIN`. Keep that origin set to the working portal address. Do not change it separately for every journal or call FastAPI directly from frontend components.

References: [Next.js self-hosting](https://nextjs.org/docs/app/guides/self-hosting), [Caddy reverse proxy](https://caddyserver.com/docs/quick-starts/reverse-proxy).

## 4. Manually create one subdomain in DNS

For the example `research.example.com`:

1. Sign in to the DNS provider managing `example.com`.
2. Add an **A** record:

   ```text
   Type: A
   Name/Host: research
   Value: YOUR_SERVER_PUBLIC_IPV4
   TTL: Provider default, or 300 seconds during initial rollout
   ```

3. Add an AAAA record only if the server is configured and reachable over IPv6. An incorrect AAAA record can break certificate issuance or browser access.
4. If your hosting platform requires a CNAME, use its documented target instead of an A record. Do not create both at the same DNS name.
5. Confirm resolution:

   ```sh
   nslookup research.example.com
   ```

6. Wait until the hostname resolves to the intended server before expecting HTTPS certificate issuance to succeed.

For each additional journal, repeat this step with a different hostname, such as `economics.example.com`.

## 5. Manually configure the journal site in Caddy

Add this block to the active Caddyfile **without removing the portal or other existing sites**:

```caddyfile
research.example.com {
    # Opening the subdomain root selects this journal's actual homepage.
    handle / {
        redir /d6eb698t/my-first-journal/home 302
    }

    # Permit only this journal's preview route, not other journals or portal pages.
    @journal path /d6eb698t/my-first-journal/*
    handle @journal {
        reverse_proxy 127.0.0.1:3000
    }

    # Permit assets required by the Next.js-rendered website.
    @assets path /_next/* /favicon.ico
    handle @assets {
        reverse_proxy 127.0.0.1:3000
    }

    # No admin, login, API, or unrelated journal routes on this public hostname.
    handle {
        respond "Not found" 404
    }
}
```

Replace the domain and **both occurrences** of the code/slug prefix. Replace `home` if a different page is the journal's homepage. Use a temporary 302 root redirect so a later homepage change is not permanently cached.

This setup preserves the current application behavior:

- `/` redirects to this journal's existing preview path on the same subdomain.
- The saved template and page content come from this journal's private copies.
- Existing menu links, which contain the code/slug prefix, continue to work.
- Current and Archives remain available beneath the same prefix.
- `PortalChrome.tsx` recognizes the preview path and omits the portal header/sidebar/footer.
- The browser cannot navigate to `/admin` or `/login` on this journal hostname through this site block.
- Server rendering still reads through the portal's internal API; there is no need to expose `/api/*` on the journal subdomain.

If Caddy runs inside Docker, replace `127.0.0.1:3000` with the frontend service address on the private container network. Loopback inside Caddy's container is not the frontend container.

For several journals, you can maintain separate reviewed site files under `/etc/caddy/journals/` and import them from the main Caddyfile. Keep each hostname mapped to exactly one journal prefix. Do not duplicate a hostname across files.

References: [Caddy handle](https://caddyserver.com/docs/caddyfile/directives/handle), [Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).

## 6. Validate configuration and enable HTTPS

On a standard Linux installation whose active config is `/etc/caddy/Caddyfile`:

```sh
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

Run reload only after validation succeeds. Use your platform's equivalent commands if Caddy runs in Docker or under another supervisor. Retain a backup of the previous working configuration.

For an individual public hostname, Caddy can obtain and renew a certificate automatically. Ensure its DNS points to the server, ports 80/443 are reachable, and any CAA restrictions allow the chosen certificate authority. This method uses individual hostnames; it does not need a wildcard certificate or a DNS-provider plugin.

Inspect certificate/reverse-proxy errors with:

```sh
sudo journalctl -u caddy --since "15 minutes ago" --no-pager
```

Reference: [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).

## 7. Verify the manually published journal

Check the root and page URLs:

```sh
curl -I https://research.example.com/
curl -I https://research.example.com/d6eb698t/my-first-journal/home
curl -I https://research.example.com/d6eb698t/my-first-journal/current
curl -I https://research.example.com/d6eb698t/my-first-journal/archives
```

Expected: the root returns a 302 to the configured homepage; valid journal pages return 200 over HTTPS. A missing page should return 404.

Also check the isolation rules:

```sh
curl -I https://research.example.com/admin
curl -I https://research.example.com/login
curl -I https://research.example.com/api/auth/me
curl -I https://research.example.com/other123/a-different-journal/home
```

These should return 404 on this hostname. They should not show the portal or another journal.

In a browser:

1. Open the new subdomain in a private window without a portal login.
2. Confirm the correct journal name, template placement, colors, footer, and HTML content.
3. Open every menu item; ensure navigation stays on the same subdomain.
4. Verify the selected page order.
5. Check Current and Archives. If the journal has no issue content, the existing empty states are expected.
6. Refresh a page directly, test mobile width, and confirm styles/assets load.
7. Confirm the editor's dashboard still works at the portal domain.

Record the journal ID, hostname, preview prefix, administrator, configuration location, and publication date in your operations log. Share the public hostname with the editor only after verification.

## 8. Understand content updates in Method A

**This is live publishing of the journal's saved copies, not an immutable publication snapshot.** When the editor saves page/template changes, those changes appear on the subdomain after refresh. Admin master templates/pages remain independent as before.

If every content update requires fresh admin approval, do not use this live route as a snapshot system. Implement publication snapshots/versioning described in `publish.md`, or build a separate reviewed static-export process. A status label alone cannot freeze content.

The editor setting Draft or NotPublished also does not remove the Caddy configuration. Define an operational rule requiring the admin to unpublish manually, or implement a dedicated published-host availability check as described below.

## 9. Manually unpublish or roll back

To take one journal offline immediately:

1. Replace only that journal's Caddy site block with:

   ```caddyfile
   research.example.com {
       respond "This journal is not currently published." 404
   }
   ```

2. Validate and reload Caddy.
3. Verify the root **and the full prefixed page URL** both return 404. This matters because visitors may have bookmarked page URLs.
4. Ask the editor to save NotPublished, or record the status change through the existing authorized workflow. Do not treat that status change as a substitute for step 1.
5. Optionally remove the DNS record later. DNS deletion alone is not immediate because clients and resolvers cache records.
6. Preserve the journal's pages/template; no database deletion is needed.

To restore it, reinstate the reviewed site block, validate/reload, and repeat browser verification. If a configuration change affects other journals, restore the prior Caddyfile and reload. This rolls back routing only; it does not restore historical journal content.

## 10. Optional implementation for clean URLs

Method A deliberately retains the prefix in the address bar. To serve `https://research.example.com/home` instead, implement these application changes once, then keep creating DNS/Caddy entries manually:

1. Maintain a controlled hostname mapping, for example:

   ```json
   {
     "research.example.com": {
       "editorCode": "d6eb698t",
       "journalSlug": "my-first-journal",
       "homeSlug": "home",
       "enabled": true
     }
   }
   ```

   A reviewed server-side configuration file is sufficient for a fully manual workflow. Do not put credentials in it. Reject duplicate/unknown hostnames and validate all route values.

2. Add `src/proxy.ts` or an equivalent server-side host resolver. Normalize the trusted incoming hostname, resolve its configured journal, and internally route `/home` to its journal renderer. Keep the browser's clean URL.
3. Separate published-host routes from portal/preview routes. Exclude required Next.js assets; block portal and mutation routes on journal hosts.
4. Change menu generation in `src/app/[editorCode]/[journalSlug]/[pageSlug]/page.tsx`, or introduce a shared renderer, so published-host links are `/home`, `/current`, `/archives`, etc. Preserve prefixed links for portal previews.
5. Update `PortalChrome.tsx` to recognize published-host rendering. Its current pathname-only rule will not identify `/home` as a standalone journal.
6. Update canonical metadata to the subdomain, and decide whether to allow search-engine indexing. Current preview metadata is noindex.
7. Maintain frontend → internal API → backend routing. `APP_ORIGIN` remains the portal origin; use a fixed internal application origin if needed for server-to-server reads, never an arbitrary request Host header.
8. For a host-aware renderer, Caddy can simply reverse proxy the approved hostname to Next.js. Retain application-level hostname allowlisting and route restrictions.
9. Test all clean URLs, direct refreshes, inactive mappings, other-journal isolation, and portal login before replacing the Method A configuration.

**A root rewrite alone is insufficient**: the current menu URLs include the editor-code/journal-slug prefix. Do not assume a DNS record or one Caddy rewrite automatically converts those links to clean URLs.

## 11. Backend changes and status enforcement

### Method A: no backend migration or new API required

The manual live-publishing runbook uses existing journal records, workflow status, and read-only preview APIs. DNS, certificate issuance, and journal-to-prefix selection are managed manually in infrastructure. No SQL inserts/updates or new backend publishing endpoint are needed.

Current behavior to remember:

- `Published` is stored on `editor_journals.status` and displayed in the admin journal list.
- The preview API currently checks editor eligibility but does not require Published status.
- The public endpoint returns current saved journal copies, not a frozen release.
- Admin Open journal links still point to the portal preview until a public-hostname feature is added.

### Optional enforcement when using clean hostnames

If Published must automatically control public availability, add a separate public-site resolution endpoint or published-host lookup that checks both the approved hostname mapping and `journal.status == "Published"`. Continue checking the owner is active/verified. Return 404 for disabled mappings or Draft/NotPublished journals.

Do not add a global Published-only check to the existing preview endpoint: editors still need to preview Draft journals. Keep preview access and published-host access distinct. Admin approval should remain a separate mapping/approval flag; an editor changing status must not authorize an arbitrary domain.

If hostname mappings must appear in the portal or survive configuration changes independently, add a migration for a unique hostname-to-journal mapping and read-only public URL fields in journal/admin responses. Provision DNS and Caddy manually; the database mapping is not itself a DNS record. For release snapshots, audit trails, or a future admin Publish button, follow the versioned publication design in `publish.md`.
