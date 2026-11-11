"""Data handed to the page renderer. Contains only public, contact-free fields."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from brief470.domain.entities import Form470


@dataclass(frozen=True, slots=True)
class StatePage:
    code: str
    name: str
    funding_year: str
    updated: date
    filed: int
    open: int
    open_equipment: int
    requests: tuple[Form470, ...]  # open requests, already sorted, contacts stripped


@dataclass(frozen=True, slots=True)
class StateSummary:
    code: str
    name: str
    filed: int
    open: int
    open_equipment: int


@dataclass(frozen=True, slots=True)
class StatesIndex:
    funding_year: str
    updated: date
    states: tuple[StateSummary, ...]


class PageRenderer(Protocol):
    def write_state_page(self, page: StatePage) -> str:
        """Render and write the page. Returns the written path."""
        ...

    def write_states_index(self, index: StatesIndex) -> str: ...
