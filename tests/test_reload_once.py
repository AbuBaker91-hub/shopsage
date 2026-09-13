"""Reloading the same catalog.json twice inserts nothing new: the second
/admin/reload is a no-op via idempotency.once (keyed by file hash), and even a
forced re-upsert cannot duplicate chunks thanks to the unique constraint."""


def _counts(conn):
    products = conn.execute("SELECT count(*) FROM products").fetchone()[0]
    chunks = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
    return products, chunks


def test_reload_twice_inserts_nothing_new(app_client, test_db):
    assert _counts(test_db) == (40, 40)  # loaded once by the fixture

    first = app_client.post("/admin/reload").json()
    assert first["ran"] is True
    assert first["result"]["new_chunks"] == 0  # upsert found every chunk already there
    assert _counts(test_db) == (40, 40)

    second = app_client.post("/admin/reload").json()
    assert second["ran"] is False  # once() short-circuited on the same file hash
    assert _counts(test_db) == (40, 40)
