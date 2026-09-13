"""Out-of-stock products are excluded from find queries but included (the
widget renders the badge from the stock field) for availability queries."""

from util import find_candidates


def _out_of_stock_target(test_db, stub_embedder):
    row = test_db.execute(
        "SELECT id, title FROM products WHERE stock = 0 ORDER BY id LIMIT 1"
    ).fetchone()
    question = f"is the {row[1]} available?"
    candidates = find_candidates(test_db, stub_embedder, question)
    assert row[0] in [p["id"] for p in candidates], "retrieval sanity check"
    return row[0], question


def test_out_of_stock_excluded_from_find(app_client, test_db, mock_provider, stub_embedder):
    pid, question = _out_of_stock_target(test_db, stub_embedder)
    mock_provider.set("intent", {"kind": "find", "product_refs": []})
    mock_provider.set("reply", {"message": "Take a look.", "product_ids": [pid], "comparison": []})

    body = app_client.post("/chat", json={"session_id": "t1", "question": question}).json()

    assert [p["id"] for p in body["products"]] == []
    assert pid in body["dropped_ids"]


def test_out_of_stock_included_for_availability(app_client, test_db, mock_provider, stub_embedder):
    pid, question = _out_of_stock_target(test_db, stub_embedder)
    mock_provider.set("intent", {"kind": "availability", "product_refs": []})
    mock_provider.set(
        "reply", {"message": "Here is that product.", "product_ids": [pid], "comparison": []}
    )

    body = app_client.post("/chat", json={"session_id": "t1", "question": question}).json()

    assert [p["id"] for p in body["products"]] == [pid]
    assert body["products"][0]["stock"] == 0  # the widget renders the badge from this
    assert pid not in body["dropped_ids"]
