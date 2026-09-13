"""Deterministic post-LLM filter. Pure function, no LLM, no I/O.

The model only proposes product ids. This filter enforces the guardrails:
- any id not in the retrieved candidate set is dropped (reason "unknown_product")
- out-of-stock products are dropped unless the question asked about availability
  (reason "out_of_stock")
- results are capped to MAX_PRODUCTS (reason "over_cap")
"""

from dataclasses import dataclass, field

MAX_PRODUCTS = 4


@dataclass
class FilterResult:
    kept_ids: list[int] = field(default_factory=list)
    dropped: list[dict] = field(default_factory=list)  # [{"id": int, "reason": str}]


def apply_filter(
    reply_ids: list[int],
    candidate_ids: list[int],
    products_by_id: dict[int, dict],
    intent_kind: str,
    cap: int = MAX_PRODUCTS,
) -> FilterResult:
    allowed = set(candidate_ids)
    seen: set[int] = set()
    kept: list[int] = []
    dropped: list[dict] = []
    for pid in reply_ids:
        if pid in seen:
            continue
        seen.add(pid)
        if pid not in allowed or pid not in products_by_id:
            dropped.append({"id": pid, "reason": "unknown_product"})
            continue
        if products_by_id[pid]["stock"] <= 0 and intent_kind != "availability":
            dropped.append({"id": pid, "reason": "out_of_stock"})
            continue
        kept.append(pid)
    for pid in kept[cap:]:
        dropped.append({"id": pid, "reason": "over_cap"})
    return FilterResult(kept_ids=kept[:cap], dropped=dropped)
