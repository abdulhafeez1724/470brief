"""Bid brief model and ports. Defined for Phase 2; nothing implements them yet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from brief470.domain.entities import Form470


@dataclass(frozen=True, slots=True)
class LineItem:
    item: str
    model: str | None = None
    quantity: str | None = None


@dataclass(frozen=True, slots=True)
class ScoringCriterion:
    name: str
    points: int | None = None


@dataclass(frozen=True, slots=True)
class Brief:
    form_number: str
    scope_summary: str
    line_items: tuple[LineItem, ...] = ()
    bid_deadline_text: str | None = None
    submission_method: str | None = None
    contact: str | None = None
    contract_term: str | None = None
    scoring_criteria: tuple[ScoringCriterion, ...] = ()
    required_attachments: tuple[str, ...] = ()
    disqualifiers: tuple[str, ...] = ()
    source_urls: tuple[str, ...] = ()


class PdfTextReader(Protocol):
    async def read_text(self, url: str) -> str: ...


class BriefSummarizer(Protocol):
    async def summarize(self, form: Form470, documents: dict[str, str]) -> Brief:
        """Build a brief from a Form 470 and its documents' text, keyed by source URL."""
        ...
