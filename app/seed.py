"""One-shot database preparation: migrations + catalog + product chunks.

Fully prepares any Postgres (local or remote/Neon) for the demo. Safe to
re-run: migrations are tracked, the catalog load is idempotent by file hash.

Usage (Windows, against a remote demo DB):
    set DATABASE_URL=postgresql://user:pass@host/db
    set EMBEDDER=stub
    .venv\\Scripts\\python.exe -m app.seed
"""

from aiforge_core.db import connect, run_migrations

from .catalog import reload_catalog
from .chat import build_embedder
from .main import CATALOG_PATH, ROOT


def main() -> None:
    conn = connect()
    applied = run_migrations(conn, ROOT / "migrations")
    print(f"migrations applied: {applied if applied else 'none (already up to date)'}")
    result, ran = reload_catalog(conn, CATALOG_PATH, build_embedder())
    print(f"catalog load ran={ran} result={result}")
    products = conn.execute("SELECT count(*) FROM products").fetchone()[0]
    chunks = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
    print(f"DB ready: {products} products, {chunks} chunks")
    conn.close()


if __name__ == "__main__":
    main()
