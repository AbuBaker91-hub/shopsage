# ShopSage: Catalog-Grounded AI Shopping Assistant with an Embeddable Widget

## Problem

Store owners want a chat assistant, but off-the-shelf bots invent products, quote wrong prices and recommend items that are out of stock. One hallucinated discount can cost real money and real trust. ShopSage is built so the model physically cannot do any of that: it can only pick ids from the live catalog, and every price, stock level and comparison number is rendered from the database.

## What it does

- Answers shopper questions with a short message plus product cards (price, stock badge, view link) drawn from database rows — never from model text
- Compares 2–3 products with a table computed in code: the three differences that matter, ordered price → weight → capacity → material
- Retrieves candidates with hybrid search (pgvector + Postgres full text) over one chunk per product
- Refuses honestly: ask for tents in a backpack store and it says the store does not carry them, with zero cards
- Embeds on any page with one script tag (CORS is enabled for the widget endpoints): `<script src="/static/widget.js" data-endpoint="/chat"></script>`
- Ships a fake storefront (`/`) so the whole flow is clickable in seconds
- Runs fully offline with `LLM_PROVIDER_ORDER=mock` and `EMBEDDER=stub` — no keys, no downloads
- Optional `scripts/shopify_sync.py` pulls a real catalog from a Shopify Storefront API (free Partner dev store)

(Loom video coming soon) · (live demo coming soon)

| The demo storefront | Grounded recommendations |
| --- | --- |
| ![Fake storefront with the widget launcher](docs/screenshots/01-storefront.png) | ![Product cards with DB prices and stock badges](docs/screenshots/03-recommendations.png) |

| Comparison computed in code | Honest about stock |
| --- | --- |
| ![Three-row compare table with DB values](docs/screenshots/04-compare-table.png) | ![Out of stock badge, no purchase link](docs/screenshots/05-out-of-stock.png) |

![The widget mounted on a blank page by a single script tag](docs/screenshots/07-embed-one-script-tag.png)
*A blank HTML file containing nothing but the script tag — the widget mounts and answers cross-origin.*

## Architecture

```mermaid
flowchart LR
  W[widget.js on any page] -->|POST /chat| API[FastAPI]
  API --> R[aiforge-core Router]
  R --> G[Gemini 2.5 Flash]
  R --> Q[Groq llama-3.3-70b]
  API --> F[filter.py + compare.py<br/>deterministic]
  API --> DB[(Postgres + pgvector<br/>products, chats, chunks,<br/>audit_log, processed_keys)]
```

Pipeline per chat: **intent** (classify find / compare / availability / other) → **retrieve** (hybrid search, k=8, chunk doc → product row) → **reply** (model sees candidates by id, title and attributes only — no prices — and may only choose those ids) → **filter** (deterministic: unknown ids dropped, out-of-stock removed unless the question was about availability, cap 4) → **render** (full DB rows returned; comparisons computed in `compare.py`). One audit row per stage, ref = chat id.

## Guardrails

- The model never sees a price and is instructed never to state one; the widget renders prices and stock badges only from DB rows returned by the API
- Any product id the model returns that was not in the retrieved candidate set is dropped and logged to the audit trail as `unknown_product`
- Out-of-stock products are removed from recommendations unless the shopper asked about availability (then they appear with an "Out of stock" badge and no purchase link)
- Comparison tables are an attribute diff computed in code from DB values — the model only phrases the sentence
- Every LLM output is validated into a Pydantic schema; validation failure means an honest "try again" message, never partial data
- Catalog reloads are idempotent by file hash; per-IP rate limiting protects free quotas

## Limits

- One store, one catalog file, one language (English) — no multi-tenant anything
- No cart, checkout, order status or payments; "View" links to the product record
- The catalog is 40 sample products; `shopify_sync.py` is documented but optional
- Retrieval is top-8 hybrid search — no re-ranker, no query rewriting
- The offline mock provider matches keywords; nuanced phrasing needs the real model
- Session memory is one browser tab; chats are stored but not used as context

## Run

```bash
cp .env.example .env       # add GEMINI_API_KEY, or set LLM_PROVIDER_ORDER=mock
make setup                 # venv, deps, dockerised pgvector Postgres, migrations
make demo                  # seeds 40 products idempotently, serves http://localhost:8000
```

Open http://localhost:8000, click the chat bubble, ask for "a light pack under 1.5 kg for a weekend hike".

Zero-key offline demo: set `LLM_PROVIDER_ORDER=mock` and `EMBEDDER=stub` in `.env` — canned intent/reply logic and a deterministic embedder, no downloads, no API calls. The default `EMBEDDER=minilm` uses real local MiniLM embeddings and needs the `demo` extra (`uv pip install -p .venv -e ".[demo]"`), which the Docker image installs already.

### Deploy (Render + Neon)

1. Neon: create a free project, enable the `vector` extension, copy `DATABASE_URL`.
2. Render: new Web Service from this repo, Docker runtime, add the env vars from `.env.example`, health check `/health`.
3. First boot runs migrations and seeds the sample catalog automatically (idempotent).
4. Confirm `https://<app>.onrender.com/health` returns `{"ok": true}`.
5. Rate limit stays on. Free Gemini quota is enough for demo traffic.

## Tests

```bash
make test   # pytest, MockProvider + StubEmbedder, no keys, no network
```

- `test_filter_unknown_id` — a model-invented id is removed and audited as `unknown_product`
- `test_price_from_db` — the API price equals the DB price even when the mock message text lies about it
- `test_out_of_stock` — excluded from a find query; included (stock=0 row for the badge) for an availability query
- `test_compare` — three products → exactly three differences, priority-ordered, values equal DB attributes
- `test_reload_once` — reloading the same catalog.json twice inserts nothing new
- `test_widget_static` — `/static/widget.js` served as JavaScript and contains `data-endpoint`

DB-backed tests use a throwaway database per test on `TEST_DATABASE_URL` (default `postgresql://postgres:postgres@localhost:5433/postgres`).

## Keywords

Shopify AI assistant, e-commerce chatbot, product recommendation AI, conversational commerce, catalog search, embeddable chat widget, pgvector, FastAPI, PostgreSQL.
