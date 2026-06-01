# Salebazzar

Salebazzar is a FastAPI deal index that keeps only API-sourced products discounted by 80% or more. It scans configured categories on a budget-aware schedule, rejects incomplete or suspicious prices, ranks qualified deals, stores them in SQLite, and serves a Bootstrap storefront plus an admin dashboard.

## Features

- Legal API adapters for SerpApi Google Shopping, DataYuge, and PricesAPI
- Six default categories: Electronics, Fashion, Home & Kitchen, Beauty, Sports, Books
- Discount, savings, quality-score sorting and storefront filters
- Deal quality score: `discount_percent * 0.6 + rating * 0.2 + popularity * 0.2`
- Amazon, Flipkart, and configurable affiliate-link rewriting
- APScheduler scan job every 18 hours by default
- Monthly SerpApi budget guard with a configurable reserve
- SQLite persistence and API usage reporting

## Install

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`, enable at least one provider, and add its API key. For DataYuge and PricesAPI, set the licensed search endpoint supplied by your account. Their adapters accept common product response fields and can be extended in `app/providers/generic.py` if your plan uses a different response shape.

The default SerpApi settings are designed for the 250-search free plan. Six categories consume six searches per full scan. The app scans every 18 hours, stops automatically after 240 searches in a calendar month, and keeps 10 searches as a buffer. Adjust `SERPAPI_MONTHLY_SEARCH_LIMIT` and `SERPAPI_MONTHLY_SEARCH_RESERVE` if your plan changes.

SerpApi discovery defaults to Google Shopping India (`gl=in`, `google_domain=google.co.in`). SerpApi results are discovery links, not commission-bearing affiliate links. Configure approved affiliate credentials or product feeds before monetizing merchant traffic.

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

The included `render.yaml` creates a free Render web service with startup scanning disabled. This is suitable for a public test site and affiliate-program application, not for production deal ingestion. Free Render web services spin down when idle and use an ephemeral filesystem, so SQLite data is not durable.

1. Push this folder to a GitHub repository. Do not commit `.env` or `80off.db`.
2. In Render, choose **New** then **Blueprint** and connect the repository.
3. Enter a public `CONTACT_EMAIL` value when Render asks.
4. Deploy the free `salebazzar` service.

Configure a persistent database and an external scheduled worker before enabling live recurring scans on a hosted environment.

## Future hooks

The scan service is the integration point for Telegram, WhatsApp, email, daily top-ten summaries, price-history snapshots, and AI deal verification. Add notifications after `_save_product` and add a price-history table before implementing charts.

## Test

```powershell
pytest
```
