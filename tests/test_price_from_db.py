"""API product prices always equal the DB price, even when the mock model's
message text claims a different number. Prices render from rows, not from text."""

from util import find_candidates


def test_price_comes_from_db_not_model_text(app_client, test_db, mock_provider, stub_embedder):
    question = "a hiking backpack for day trips"
    good = next(p for p in find_candidates(test_db, stub_embedder, question) if p["stock"] > 0)
    assert good["price_cents"] != 100  # the lie below must differ from the DB

    mock_provider.set("intent", {"kind": "find", "product_refs": []})
    mock_provider.set(
        "reply",
        {
            "message": "This one is a bargain at just $1.00!",
            "product_ids": [good["id"]],
            "comparison": [],
        },
    )

    body = app_client.post("/chat", json={"session_id": "t1", "question": question}).json()

    db_row = app_client.get(f"/products/{good['id']}").json()
    assert body["products"][0]["id"] == good["id"]
    assert body["products"][0]["price_cents"] == db_row["price_cents"] == good["price_cents"]
    # the model's fake price never reaches any structured field
    assert body["products"][0]["price_cents"] != 100
