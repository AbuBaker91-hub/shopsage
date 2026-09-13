"""Optional: pull real products from a Shopify Storefront API into samples/catalog.json.

The demo does not need this — samples/catalog.json ships with 40 products.
To use it, create a free Shopify Partner dev store, then set
SHOPIFY_STORE_DOMAIN (e.g. my-store.myshopify.com) and SHOPIFY_STOREFRONT_TOKEN
and run: python scripts/shopify_sync.py
"""

import json
import os
import urllib.request

QUERY = """{ products(first: 100) { nodes { handle title description tags
  variants(first: 1) { nodes { price { amount } quantityAvailable } } } } }"""


def main() -> None:
    url = f"https://{os.environ['SHOPIFY_STORE_DOMAIN']}/api/2024-10/graphql.json"
    req = urllib.request.Request(
        url,
        data=json.dumps({"query": QUERY}).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Storefront-Access-Token": os.environ["SHOPIFY_STOREFRONT_TOKEN"],
        },
    )
    with urllib.request.urlopen(req) as resp:
        nodes = json.load(resp)["data"]["products"]["nodes"]
    items = [
        {
            "handle": n["handle"],
            "title": n["title"],
            "description": n["description"],
            "category": "shopify",
            "tags": n["tags"],
            "price_cents": int(float(n["variants"]["nodes"][0]["price"]["amount"]) * 100),
            "stock": n["variants"]["nodes"][0]["quantityAvailable"] or 0,
            "attributes": {},
        }
        for n in nodes
        if n["variants"]["nodes"]
    ]
    with open("samples/catalog.json", "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
    print(f"wrote {len(items)} products to samples/catalog.json")


if __name__ == "__main__":
    main()
