"""Pydantic schemas: every LLM output is validated into one of these."""

from typing import Literal

from pydantic import BaseModel, Field


class Intent(BaseModel):
    """Output of the intent prompt."""

    kind: Literal["find", "compare", "availability", "other"] = "find"
    product_refs: list[str] = Field(default_factory=list)


class ComparisonRow(BaseModel):
    attribute: str
    values: dict[str, str] = Field(default_factory=dict)


class Reply(BaseModel):
    """Output of the reply prompt. The model returns ids only; prices, stock
    and the comparison table are always taken from the database."""

    message: str
    product_ids: list[int] = Field(default_factory=list)
    comparison: list[ComparisonRow] = Field(default_factory=list)


class ChatRequest(BaseModel):
    session_id: str
    question: str
