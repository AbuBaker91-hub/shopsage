"""The model returns an id that is not in the candidate set -> it is removed
and the drop is recorded in the audit log with reason "unknown_product"."""

from aiforge_core import audit
from util import find_candidates

from app.filter import apply_filter


def test_apply_filter_drops_unknown_id():
    products = {1: {"id": 1, "stock": 5}}
    result = apply_filter([1, 999], [1], products, "find")
    assert result.kept_ids == [1]
    assert result.dropped == [{"id": 999, "reason": "unknown_product"}]


def test_unknown_id_removed_and_audited(app_client, test_db, mock_provider, stub_embedder):
    question = "a light backpack for a weekend hike"
    good = next(p for p in find_candidates(test_db, stub_embedder, question) if p["stock"] > 0)
    mock_provider.set("intent", {"kind": "find", "product_refs": []})
    mock_provider.set(
        "reply",
        {"message": "Try this one.", "product_ids": [good["id"], 999999], "comparison": []},
    )

    body = app_client.post(
        "/chat", json={"session_id": "t1", "question": question}
    ).json()

    returned_ids = [p["id"] for p in body["products"]]
    assert good["id"] in returned_ids
    assert 999999 not in returned_ids
    assert 999999 in body["dropped_ids"]

    rows = audit.rows_for(test_db, str(body["chat_id"]))
    assert [r["stage"] for r in rows] == ["intent", "retrieve", "reply", "filter"]
    filter_row = rows[-1]
    assert "unknown_product" in filter_row["detail"]
    assert "999999" in filter_row["detail"]
