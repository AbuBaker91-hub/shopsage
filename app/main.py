"""FastAPI wiring: POST /chat, GET /products, GET /products/{id},
POST /admin/reload, and the demo storefront at GET /."""

import mimetypes
from pathlib import Path

from aiforge_core import audit
from aiforge_core.app import create_app
from aiforge_core.db import connect, run_migrations
from aiforge_core.llm import AllProvidersFailed, ValidationFailed
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import catalog
from .chat import build_embedder, build_router, handle_chat
from .schemas import ChatRequest

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "samples" / "catalog.json"

# Windows registries sometimes map .js to text/plain; pin it for everyone.
mimetypes.add_type("text/javascript", ".js")


def create_shopsage_app(conn, router, embedder) -> FastAPI:
    app = create_app("shopsage", static_dir=ROOT / "static")
    # the widget embeds on any storefront with one script tag, so /chat and
    # /products must answer cross-origin requests
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    app.state.conn = conn
    app.state.router = router
    app.state.embedder = embedder

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(ROOT / "static" / "demo.html")

    @app.get("/products")
    def products() -> list[dict]:
        return catalog.all_products(app.state.conn)

    @app.get("/products/{product_id}")
    def product(product_id: int) -> dict:
        row = catalog.get_product(app.state.conn, product_id)
        if row is None:
            raise HTTPException(status_code=404, detail="product not found")
        return row

    @app.post("/chat")
    def chat(req: ChatRequest) -> dict:
        try:
            return handle_chat(
                app.state.conn, app.state.router, app.state.embedder,
                req.session_id, req.question,
            )
        except (ValidationFailed, AllProvidersFailed) as e:
            # honest failure: no partial write, no made-up products
            audit.record(
                app.state.conn, "chat", ref="", ok=False,
                detail=f"{type(e).__name__}: {e}",
            )
            return {
                "chat_id": None,
                "message": "Sorry - I could not process that right now. Please try again.",
                "products": [],
                "comparison": [],
                "dropped_ids": [],
            }

    @app.post("/admin/reload")
    def admin_reload() -> dict:
        result, ran = catalog.reload_catalog(app.state.conn, CATALOG_PATH, app.state.embedder)
        return {"ran": ran, "result": result}

    return app


def production_app() -> FastAPI:
    """Uvicorn factory: migrations + idempotent catalog load, then the app.

    uvicorn app.main:production_app --factory
    """
    conn = connect()
    run_migrations(conn, ROOT / "migrations")
    embedder = build_embedder()
    catalog.reload_catalog(conn, CATALOG_PATH, embedder)
    router = build_router(ROOT / "prompts")
    return create_shopsage_app(conn, router, embedder)
