"""Product comparison computed in code. Pure function, no LLM, no I/O.

The model never produces comparison numbers: the attribute diff comes straight
from database rows. Attributes that differ are kept, ordered by a fixed
priority list (price, weight, capacity, material, then alphabetical), capped
at three.
"""

PRIORITY = ("price", "weight", "capacity", "material")
MAX_DIFFERENCES = 3


def format_price(price_cents: int) -> str:
    return f"${price_cents / 100:.2f}"


def _rank(attribute: str) -> tuple[int, str]:
    name = attribute.lower()
    for i, keyword in enumerate(PRIORITY):
        if keyword in name:
            return (i, name)
    return (len(PRIORITY), name)


def diff(products: list[dict], top: int = MAX_DIFFERENCES) -> list[dict]:
    """For 2-3 product rows, return [{"attribute", "values": {product_id: value}}]
    for the top differing attributes. Values come from the DB rows only."""
    if len(products) < 2:
        return []
    differing: dict[str, dict[str, str]] = {}

    prices = {str(p["id"]): format_price(p["price_cents"]) for p in products}
    if len(set(prices.values())) > 1:
        differing["price"] = prices

    names: set[str] = set()
    for p in products:
        names |= set((p.get("attributes") or {}).keys())
    for name in names:
        values = {
            str(p["id"]): str((p.get("attributes") or {}).get(name, "-")) for p in products
        }
        if len(set(values.values())) > 1:
            differing[name] = values

    ordered = sorted(differing, key=_rank)[:top]
    return [{"attribute": name, "values": differing[name]} for name in ordered]
