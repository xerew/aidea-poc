# Self-hosted Matomo (zero-cost web analytics)

Matomo runs on your own VM: no cost, cookieless, GDPR-friendly, and the data
never leaves your server. It is **fully opt-in** — the platform ships with an
inert analytics client and Matomo lives in an overlay compose file, so nothing
changes until you follow the steps below.

Everything runs at `https://analytics.<your domain>` (e.g.
`https://analytics.aidea-hub.eu`) behind the existing Caddy proxy, which issues
the TLS certificate automatically.

## 1. DNS

Add an **A record** for the analytics subdomain pointing at the VM:

```
analytics.aidea-hub.eu.  A  83.212.202.56
```

Wait for it to resolve before starting (Caddy needs it to issue the certificate).

## 2. Secrets

Add two strong passwords to your **root `.env`** (same file that holds
`POSTGRES_PASSWORD`, `DOMAIN`, etc.):

```
MATOMO_DB_PASSWORD=<a strong password>
MATOMO_DB_ROOT_PASSWORD=<another strong password>
```

## 3. Start Matomo

From the repo root on the VM, bring the stack up **with the overlay**:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.matomo.yml up -d
```

This starts `matomo-db` + `matomo` and mounts the analytics site snippet into
Caddy. Give Caddy a minute to obtain the certificate for the subdomain.

> From now on, always include **both** `-f` files when running compose commands
> for this stack, so Matomo and its Caddy route stay up.

## 4. Complete the web installer

Open `https://analytics.aidea-hub.eu` and follow the wizard:

- **Database** — already filled in from the env vars; just continue.
- **Super user** — create your Matomo admin login.
- **Add your first website** — Name `AIDEA`, URL `https://aidea-hub.eu`. Note the
  **Site ID** it assigns (normally `1`).

## 5. Tell Matomo it's behind an HTTPS proxy

Caddy terminates TLS and talks to Matomo over plain HTTP, so Matomo must trust
the proxy (otherwise you can get redirect loops). Edit its config once:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.matomo.yml exec matomo \
  sh -lc 'vi /var/www/html/config/config.ini.php'
```

Under the `[General]` section add:

```ini
assume_secure_protocol = 1
proxy_client_headers[] = "HTTP_X_FORWARDED_FOR"
proxy_host_headers[] = "HTTP_X_FORWARDED_HOST"
```

Confirm `trusted_hosts[]` already lists `analytics.aidea-hub.eu` (the installer
adds it). Save and exit.

## 6. Turn it on in the platform

Matomo is now collecting, but the frontend won't send anything until it's built
with the analytics vars. Add to your **root `.env`**:

```
VITE_ANALYTICS_PROVIDER=matomo
VITE_MATOMO_URL=https://analytics.aidea-hub.eu/
VITE_MATOMO_SITE_ID=1
```

Then rebuild the frontend:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.matomo.yml up -d --build frontend
```

(These are baked in at build time, so a rebuild is required — env changes alone
won't take effect.)

## 7. Verify

Open the platform and click around a few pages. In Matomo go to
**Visitors → Visits Log** — you should see the visits appear. Page views are
sent on every SPA route change.

## Notes

- **Cookieless.** The client calls `disableCookies`, so under EU ePrivacy rules a
  consent banner is typically **not** required. Still, add a short line to your
  Privacy Policy mentioning self-hosted, cookieless Matomo for transparency.
- **Backups.** Matomo data lives in the `matomo_db_data` volume — add it to your
  backup routine if you want history preserved.
- **Performance (optional, at scale).** For higher traffic, disable browser-side
  archiving in Matomo's settings and run `core:archive` on a cron; not needed at
  pilot volume.
- **Disable again.** Remove the `VITE_ANALYTICS_*` vars and rebuild the frontend
  to stop sending; drop the second `-f` file to stop running Matomo.
