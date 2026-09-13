"""The intent -> retrieve -> reply -> filter -> compare pipeline.

Every model call goes through Router.generate_json with a Pydantic schema.
The model only ever contributes the message text and candidate ids; prices,
stock and comparison values always come from the database. One audit row per
stage (intent, retrieve, reply, filter), ref = chat id.
"""

import json
import os

import psycopg
from aiforge_core import audit, vectorstore
from aiforge_core.llm import Router, router_from_env

from . import catalog, compare
from .filter import apply_filter
from .schemas import Intent, Reply

RETRIEVE_K = 8


def build_embedder():
    """EMBEDDER=stub -> deterministic offline embedder; default is real MiniLM."""
    if os.getenv("EMBEDDER", "minilm").strip().lower() == "stub":
        from aiforge_core.embed import StubEmbedder

        return StubEmbedder()
    from aiforge_core.embed import Embedder

    return Embedder()


def build_router(prompts_dir) -> Router:
    """LLM_PROVIDER_ORDER=mock -> offline canned provider; else gemini/groq."""
    if os.getenv("LLM_PROVIDER_ORDER", "gemini,groq").strip().lower() == "mock":
        from .offline import OfflineProvider

        return Router([OfflineProvider()], prompts_dir=prompts_dir)
    return router_from_env(prompts_dir)


def handle_chat(
    conn: psycopg.Connection, router: Router, embedder, session_id: str, question: str
) -> dict:
    chat_id = conn.execute(
        "INSERT INTO chats (session_id, question) VALUES (%s, %s) RETURNING id",
        (session_id, question),
    ).fetchone()[0]
    ref = str(chat_id)
    qhash = audit.input_hash(question)

    # 1. intent
    intent_res = router.generate_json("intent", {"question": question}, Intent)
    intent: Intent = intent_res.data
    audit.record(
        conn, "intent", ref=ref, input_hash=qhash, prompt_version=intent_res.prompt_version,
        ok=True, detail=json.dumps({"kind": intent.kind, "product_refs": intent.product_refs}),
    )

    # 2. retrieve: hybrid search over product chunks, chunk doc -> product row
    query = " ".join([question, *intent.product_refs])
    chunks = vectorstore.hybrid(conn, query, RETRIEVE_K, embedder)
    handles = [c.doc.removeprefix("product:") for c in chunks]
    candidates = catalog.products_by_handles(conn, handles)
    candidate_ids = [p["id"] for p in candidates]
    audit.record(
        conn, "retrieve", ref=ref, input_hash=qhash, ok=True,
        detail=json.dumps({"candidate_ids": candidate_ids}),
    )

    # 3. reply: candidates listed by id, title and attributes only — never prices
    candidate_payload = [
        {"id": p["id"], "title": p["title"], "attributes": p["attributes"]} for p in candidates
    ]
    reply_res = router.generate_json(
        "reply", {"question": question, "candidates": candidate_payload}, Reply
    )
    reply: Reply = reply_res.data
    audit.record(
        conn, "reply", ref=ref, input_hash=qhash, prompt_version=reply_res.prompt_version,
        ok=True, detail=json.dumps({"product_ids": reply.product_ids}),
    )

    # 4. deterministic filter: unknown ids out, out-of-stock out (unless
    # availability), cap 4
    by_id = {p["id"]: p for p in candidates}
    result = apply_filter(reply.product_ids, candidate_ids, by_id, intent.kind)
    audit.record(
        conn, "filter", ref=ref, input_hash=qhash, ok=True,
        detail=json.dumps({"kept_ids": result.kept_ids, "dropped": result.dropped}),
    )

    # 5. render: full DB rows; comparison computed in code, model output ignored
    products = [by_id[pid] for pid in result.kept_ids]
    comparison = (
        compare.diff(products[:3]) if intent.kind == "compare" and len(products) >= 2 else []
    )
    response = {
        "chat_id": chat_id,
        "message": reply.message,
        "products": products,
        "comparison": comparison,
        "dropped_ids": [d["id"] for d in result.dropped],
    }
    conn.execute(
        "UPDATE chats SET reply_json = %s, prompt_version = %s WHERE id = %s",
        (json.dumps(response, default=str), reply_res.prompt_version, chat_id),
    )
    return response
