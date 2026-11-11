"""Ports (interfaces) the application layer depends on. Infrastructure implements them."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol

from brief470.domain.entities import Form470, Form470Row, SyncResult
from brief470.domain.vendors import Vendor


class Clock(Protocol):
    def now(self) -> datetime: ...

    def today(self) -> date: ...


class Form470Source(Protocol):
    async def fetch(self, funding_year: str, state: str | None = None) -> list[Form470Row]: ...


class VendorSource(Protocol):
    async def fetch(self, state: str) -> list[Vendor]: ...


class Form470Repository(Protocol):
    def load(self, funding_year: str) -> list[Form470]:
        """Best available snapshot: private (with contacts) if present, else public."""
        ...

    def load_private(self, funding_year: str) -> list[Form470]:
        """Snapshot with contact details. Empty when it was never written on this machine."""
        ...

    def save_public(self, funding_year: str, forms: Sequence[Form470]) -> None: ...

    def save_private(self, funding_year: str, forms: Sequence[Form470]) -> None: ...

    def load_last_sync(self) -> SyncResult | None: ...

    def save_last_sync(self, result: SyncResult) -> None: ...


class TableWriter(Protocol):
    """Writes rows to a named table (CSV file locally). Returns where it was written."""

    def write(self, name: str, header: Sequence[str], rows: Sequence[Sequence[str]]) -> str: ...
