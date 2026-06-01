# Salebazzar

Salebazzar is a FastAPI deal index that keeps API-sourced products discounted by 50% or more. It scans configured categories on a budget-aware schedule, rejects incomplete or suspicious prices, ranks qualified deals, stores them in SQLite, and serves a Bootstrap storefront plus an admin dashboard.

## Features

- Amazon Associates tracking-link support
- Amazon Creators API configuration placeholders for approved accounts
- Licensed Rainforest API adapter for automated Amazon.in deal discovery
- Optional legal API adapters for DataYuge and PricesAPI
- Six default categories: Electronics, Fashion, Home & Kitchen, Beauty, Sports, Books
- Discount, savings, quality-score sorting and storefront filters
- Deal quality score: `discount_percent * 0.6 + rating * 0.2 + popularity * 0.2`
- Amazon, Flipkart, and configurable affiliate-link rewriting
- APScheduler scan job every 18 hours by default
- SQLite persistence and API usage reporting

## Install

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and add approved provider credentials. Amazon Associates tracking links work with `AMAZON_AFFILIATE_TAG`. Amazon product-catalog search requires separate Creators API approval and credentials. For DataYuge and PricesAPI, set the licensed search endpoint supplied by your account.

## Amazon Creators API

Amazon catalog search is not enabled automatically by an Associates ID. Amazon requires Creators API eligibility, registration, and a generated public/private credential pair. Keep the private key out of source control. Once Amazon issues credentials, add them to `.env` or your private hosting environment:

```text
AMAZON_CREATORS_API_ENABLED=true
AMAZON_CREATORS_API_PUBLIC_KEY=...
AMAZON_CREATORS_API_PRIVATE_KEY=...
AMAZON_CREATORS_API_MARKETPLACE=www.amazon.in
```

The final Creators API adapter should be connected after Amazon grants access so it can be tested against the current official SDK and your approved India marketplace account.

## Automated Amazon Deal Discovery

Salebazzar supports the licensed [Rainforest API](https://www.rainforestapi.com/) as an optional interim Amazon.in deal source. Register with Rainforest, confirm that your intended affiliate-site usage is covered by your plan, and add the issued API key privately:

```text
RAINFOREST_ENABLED=true
RAINFOREST_API_KEY=...
RAINFOREST_AMAZON_DOMAIN=amazon.in
RAINFOREST_DEALS_MAX_PAGE=1
RUN_SCAN_ON_STARTUP=true
```

The adapter calls Rainforest's documented Amazon Deals endpoint, categorizes returned offers locally, applies the configured minimum-discount rule, and adds `AMAZON_AFFILIATE_TAG` to eligible Amazon links. `RAINFOREST_DEALS_MAX_PAGE` controls pagination and API-credit usage. Real-time requests are capped at five pages. Do not commit the Rainforest key to GitHub.

## Manual Amazon Deals

Until Creators API access is granted, open `/admin` and use the password-protected manual publisher. Add `ADMIN_PASSWORD` to your private `.env` or Render environment settings. Use Amazon Associates SiteStripe to obtain the original Amazon.in product URL. Salebazzar rejects non-Amazon links and deals below the configured minimum discount, then adds your `AMAZON_AFFILIATE_TAG` automatically.

Do not commit `ADMIN_PASSWORD` to GitHub. On Render's free plan, manually entered SQLite records can disappear after a redeploy or service restart because the filesystem is ephemeral.

## Authorized Message Imports

Open `/admin` to paste a batch of deal messages or upload a UTF-8 `.txt` export you are permitted to reuse. The importer extracts merchant links and explicit discounts, categorizes posts, rejects deals below the configured threshold, and reports skipped messages. Posts without an explicit discount are left out for review because a sale price alone does not prove the minimum discount.

Start the server:

```powershell
python -m uvicorn app.main:app --reload
```

On Windows, you can also double-click `run_80off.cmd`.

Open `http://127.0.0.1:8000` for deals and `http://127.0.0.1:8000/admin` for scan metrics. Set `RUN_SCAN_ON_STARTUP=true` to run immediately; otherwise the first scan starts after the configured interval.

To run the app from any terminal folder:

```powershell
python -m uvicorn app.main:app --reload --app-dir "C:\path\to\Salebazzar"
```

## Production

Run a single scheduler-enabled application process so scans are not duplicated:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For horizontal scaling, move `run_scan_sync` into a dedicated worker and run the web tier without its local scheduler. Place the application behind a TLS reverse proxy, keep `.env` out of source control, and use a managed database when the catalog grows.

## Free Render Demo

The included `render.yaml` creates a free Render web service for the public Amazon-focused demo. This is suitable for an affiliate-program application, not for production deal ingestion. Free Render web services spin down when idle and use an ephemeral filesystem, so SQLite data is not durable.

1. Push this folder to a GitHub repository. Do not commit `.env` or `80off.db`.
2. In Render, choose **New** then **Blueprint** and connect the repository.
3. Deploy the free `salebazzar` service.

Configure a persistent database and an external scheduled worker before enabling live recurring scans on a hosted environment.

## Future hooks

The scan service is the integration point for Telegram, WhatsApp, email, daily top-ten summaries, price-history snapshots, and AI deal verification. Add notifications after `_save_product` and add a price-history table before implementing charts.

## Test

```powershell
pytest
```
