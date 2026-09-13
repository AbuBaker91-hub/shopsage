"""Comparisons are computed in code: exactly three differences, ordered by the
fixed priority list (price, weight, capacity, material, else alphabetical),
with every value taken from DB attributes."""

from util import find_candidates

from app.compare import diff, format_price


def _row(pid, price_cents, **attrs):
    return {"id": pid, "price_cents": price_cents, "attributes": attrs}


def test_three_products_three_priority_ordered_differences():
    a = _row(1, 7900, size="S", capacity_l=22, weight_kg=0.9, material="ripstop nylon")
    b = _row(2, 12900, size="S", capacity_l=38, weight_kg=1.4, material="210D nylon")
    c = _row(3, 24900, size="S", capacity_l=65, weight_kg=2.4, material="Cordura")

    rows = diff([a, b, c])

    assert [r["attribute"] for r in rows] == ["price", "weight_kg", "capacity_l"]
    assert rows[0]["values"] == {"1": "$79.00", "2": "$129.00", "3": "$249.00"}
    assert rows[1]["values"] == {"1": "0.9", "2": "1.4", "3": "2.4"}
    assert rows[2]["values"] == {"1": "22", "2": "38", "3": "65"}


def test_identical_attributes_are_not_differences():
    a = _row(1, 5000, size="M", material="nylon")
    b = _row(2, 5000, size="L", material="nylon")
    rows = diff([a, b])
    assert [r["attribute"] for r in rows] == ["size"]  # same price, same material


def test_compare_endpoint_returns_three_db_valued_rows(
    app_client, test_db, mock_provider, stub_embedder
):
    question = "compare hiking backpacks for a weekend trip"
    in_stock = [p for p in find_candidates(test_db, stub_embedder, question) if p["stock"] > 0]
    picks = in_stock[:3]
    assert len(picks) == 3, "retrieval sanity check"

    mock_provider.set("intent", {"kind": "compare", "product_refs": []})
    mock_provider.set(
        "reply",
        {
            "message": "Here is how they differ.",
            "product_ids": [p["id"] for p in picks],
            "comparison": [],  # even if the model sent rows, they would be ignored
        },
    )

    body = app_client.post("/chat", json={"session_id": "t1", "question": question}).json()

    assert len(body["comparison"]) == 3
    by_id = {str(p["id"]): p for p in picks}
    for row in body["comparison"]:
        for pid, value in row["values"].items():
            if row["attribute"] == "price":
                assert value == format_price(by_id[pid]["price_cents"])
            else:
                assert value == str(by_id[pid]["attributes"][row["attribute"]])
