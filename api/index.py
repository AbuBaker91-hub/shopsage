"""Vercel serverless entrypoint: exposes the ASGI `app` served at /api/index.

Cold start applies migrations (idempotent, fast no-op once applied) but never
loads the catalog — the demo database is seeded exactly once with
`python -m app.seed`. Everything is configured by env vars: DATABASE_URL,
LLM_PROVIDER_ORDER (mock = keyless offline provider), EMBEDDER (stub = no
model downloads), APP_RATE_LIMIT_PER_MIN.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg  # noqa: E402
from aiforge_core.db import connect, run_migrations  # noqa: E402

from app.chat import build_embedder, build_router  # noqa: E402
from app.main import ROOT, create_shopsage_app  # noqa: E402


class ReconnectingConnection:
    """Tiny psycopg connection proxy for serverless: connects lazily and
    retries once when a pooled connection was dropped between invocations.
    The whole app talks to the DB through `conn.execute`, so proxying that
    single method covers every query path."""

    def __init__(self, factory):
        self._factory = factory
        self._conn = None

    def _get(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = self._factory()
        return self._conn

    def execute(self, *args, **kwargs):
        try:
            return self._get().execute(*args, **kwargs)
        except (psycopg.OperationalError, psycopg.InterfaceError):
            self._conn = None  # stale pooled connection: reconnect and retry once
            return self._get().execute(*args, **kwargs)

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()


conn = ReconnectingConnection(connect)
run_migrations(conn, ROOT / "migrations")
app = create_shopsage_app(conn, build_router(ROOT / "prompts"), build_embedder())
