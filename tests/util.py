"""Small helpers shared by the guardrail tests."""

from aiforge_core import vectorstore

from app import catalog
from app.chat import RETRIEVE_K


def find_candidates(conn, embedder, question: str) -> list[dict]:
    """Product rows the pipeline will retrieve for this question (same hybrid
    search, same k), so tests can pick ids that are truly in the candidate set."""
    chunks = vectorstore.hybrid(conn, question, RETRIEVE_K, embedder)
    handles = [c.doc.removeprefix("product:") for c in chunks]
    return catalog.products_by_handles(conn, handles)
