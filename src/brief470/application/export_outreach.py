from __future__ import annotations

from dataclasses import dataclass

from brief470.application.list_open import select_open
from brief470.domain.entities import Contact
from brief470.domain.ports import Clock, Form470Repository, TableWriter

OUTREACH_HEADER: tuple[str, ...] = (
    "entity",
    "city",
    "category",
    "service_types",
    "allowable_contract_date",
    "contact_name",
    "contact_email",
    "technical_contact_name",
    "technical_contact_email",
    "has_consultant",
    "form_470_number",
    "form_pdf_url",
    "rfp_urls",
)


class NoPrivateDataError(RuntimeError):
    """Raised when no local snapshot with contact details exists yet."""


@dataclass(frozen=True, slots=True)
class OutreachExportResult:
    path: str
    rows: int


def _name(c: Contact | None) -> str:
    return (c.name or "") if c else ""


def _email(c: Contact | None) -> str:
    return (c.email or "") if c else ""


class ExportOutreachCsv:
    def __init__(self, repo: Form470Repository, writer: TableWriter, clock: Clock) -> None:
        self._repo = repo
        self._writer = writer
        self._clock = clock

    def execute(self, funding_year: str, state: str) -> OutreachExportResult:
        state = state.upper()
        forms = self._repo.load_private(funding_year)
        if not any(f.state == state for f in forms):
            raise NoPrivateDataError(
                f"No local contact data for {state}. Run `brief470 sync --state {state}` first."
            )
        today = self._clock.today()
        rows = [
            [
                f.entity_name,
                f.city or "",
                "/".join(c.short for c in f.categories),
                "; ".join(f.service_types),
                f.allowable_contract_date.isoformat() if f.allowable_contract_date else "",
                _name(f.contact),
                _email(f.contact),
                _name(f.technical_contact),
                _email(f.technical_contact),
                "yes" if f.has_consultant else "no",
                f.number,
                f.form_pdf_url or "",
                " ".join(f.rfp_document_urls),
            ]
            for f in select_open(forms, today, state)
        ]
        name = f"exports/{state}_open_{today.isoformat()}.csv"
        path = self._writer.write(name, OUTREACH_HEADER, rows)
        return OutreachExportResult(path=path, rows=len(rows))
