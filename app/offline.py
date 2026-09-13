"""Offline demo provider: LLM_PROVIDER_ORDER=mock runs the full demo with no
API keys and no downloads.

Implements the aiforge-core provider protocol. Intent is classified with
keyword rules and the reply only ever echoes ids that are actually present in
the candidate list of the rendered prompt, so the guardrail pipeline behaves
exactly as it does with a real model. Documented limitation: it matches on
keywords, so phrasing outside the canned vocabulary falls back to "we do not
carry that".
"""

import json
import re

CATALOG_WORDS = {
    "backpack", "backpacks", "pack", "packs", "daypack", "rucksack", "bag",
    "hike", "hiking", "trek", "trail", "travel", "carry", "capacity", "liter",
    "litre", "lightweight", "light", "ultralight", "frame", "gear", "weekend",
}
COMPARE_WORDS = ("compare", " vs ", "versus", "difference", "differences")
AVAILABILITY_WORDS = ("in stock", "stock", "available", "availability")
STOPWORDS = {"the", "a", "an", "and", "or", "for", "with", "me", "my", "of",
             "is", "are", "in", "to", "you", "do", "under", "over", "kg", "l"}

_QUESTION_RE = re.compile(r"Shopper question:\s*(.+)")
_CANDIDATE_RE = re.compile(r'"id":\s*(\d+),\s*\n\s*"title":\s*"([^"]*)"')


class OfflineProvider:
    """Canned, deterministic stand-in for a real LLM provider."""

    name = "mock"

    def complete(self, prompt: str, json_schema: dict) -> str:
        prompt_name = json_schema.get("x-prompt-name", "")
        m = _QUESTION_RE.search(prompt)
        question = m.group(1).strip().lower() if m else ""
        if prompt_name == "intent":
            return json.dumps({"kind": self._kind(question), "product_refs": []})
        return json.dumps(self._reply(question, prompt))

    @staticmethod
    def _kind(question: str) -> str:
        if any(w in question for w in COMPARE_WORDS):
            return "compare"
        if any(w in question for w in AVAILABILITY_WORDS):
            return "availability"
        if any(w in question for w in CATALOG_WORDS):
            return "find"
        return "other"

    def _reply(self, question: str, prompt: str) -> dict:
        candidates = _CANDIDATE_RE.findall(prompt)  # [(id, title), ...] in rank order
        qtokens = {t for t in re.split(r"[^a-z0-9]+", question) if t and t not in STOPWORDS}
        named = [
            int(cid)
            for cid, title in candidates
            if qtokens & {t for t in re.split(r"[^a-z0-9]+", title.lower()) if t}
        ]
        if named:
            ids = named[:6]
        elif any(w in question for w in CATALOG_WORDS):
            ids = [int(cid) for cid, _ in candidates[:6]]
        else:
            ids = []
        if not ids:
            message = ("Sorry - we do not carry that. I can help you find hiking "
                       "backpacks from our catalog.")
        elif self._kind(question) == "compare":
            message = "Here is how they differ, side by side."
        elif self._kind(question) == "availability":
            message = "Here is the current availability, straight from our catalog."
        else:
            message = "Here are a few options from our catalog that match what you asked for."
        return {"message": message, "product_ids": ids, "comparison": []}
