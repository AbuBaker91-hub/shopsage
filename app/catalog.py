"""Catalog loading and product queries.

samples/catalog.json -> products table + one chunk per product
(doc = "product:<handle>", text = title + description + attributes).
Reloading is idempotent by file hash (idempotency.once) and, one level below,
by the chunks unique constraint (re-upserting inserts nothing new).
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import psycopg
from aiforge_core import idempotency, vectorstore

CHUNK_PAGE = 1  # non-null so the chunks UNIQUE(doc, page, section, text) applies

_COLS = (
    "id, handle, title, description, category, tags_json, "
    "price_cents, stock, attributes_json, updated_at"
)


def product_text(item: dict) -> str:
    attrs = ", ".join(f"{k}: {v}" for k, v in sorted(item.get("attributes", {}).items()))
    return f"{item['title']}. {item.get('description', '')} {attrs}".strip()


def load_catalog(conn: psycopg.Connection, path: str | Path, embedder) -> dict:
    """Upsert every product and its chunk. Returns {"products", "new_chunks"}."""
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    chunks = []
    for item in items:
        conn.execute(
            """INSERT INTO products (handle, title, description, category, tags_json,
                                     price_cents, stock, attributes_json, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
               ON CONFLICT (handle) DO UPDATE SET
                 title = EXCLUDED.title,
                 description = EXCLUDED.description,
                 category = EXCLUDED.category,
                 tags_json = EXCLUDED.tags_json,
                 price_cents = EXCLUDED.price_cents,
                 stock = EXCLUDED.stock,
                 attributes_json = EXCLUDED.attributes_json,
                 updated_at = now()""",
            (
                item["handle"],
                item["title"],
                item.get("description", ""),
                item.get("category", ""),
                json.dumps(item.get("tags", [])),
                item["price_cents"],
                item["stock"],
                json.dumps(item.get("attributes", {})),
            ),
        )
        chunks.append(
            {
                "doc": f"product:{item['handle']}",
                "page": CHUNK_PAGE,
                "section": item["handle"],
                "text": product_text(item),
            }
        )
    new_chunks = vectorstore.upsert(conn, chunks, embedder)
    return {"products": len(items), "new_chunks": new_chunks}


def reload_catalog(conn: psycopg.Connection, path: str | Path, embedder) -> tuple[dict, bool]:
    """Load the catalog at most once per file content. Returns (result, ran)."""
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    k = idempotency.key("catalog_reload", digest)
    return idempotency.once(conn, k, lambda: load_catalog(conn, path, embedder))


def _to_dict(row) -> dict[str, Any]:
    return {
        "id": row[0],
        "handle": row[1],
        "title": row[2],
        "description": row[3],
        "category": row[4],
        "tags": row[5],
        "price_cents": row[6],
        "stock": row[7],
        "attributes": row[8],
        "updated_at": row[9].isoformat(),
    }


def all_products(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(f"SELECT {_COLS} FROM products ORDER BY id").fetchall()  # noqa: S608
    return [_to_dict(r) for r in rows]


def get_product(conn: psycopg.Connection, product_id: int) -> dict | None:
    row = conn.execute(
        f"SELECT {_COLS} FROM products WHERE id = %s", (product_id,)
    ).fetchone()
    return _to_dict(row) if row else None


def products_by_handles(conn: psycopg.Connection, handles: list[str]) -> list[dict]:
    """Rows for the given handles, preserving the given (retrieval) order."""
    if not handles:
        return []
    rows = conn.execute(
        f"SELECT {_COLS} FROM products WHERE handle = ANY(%s)", (handles,)
    ).fetchall()
    by_handle = {r[1]: _to_dict(r) for r in rows}
    return [by_handle[h] for h in handles if h in by_handle]
