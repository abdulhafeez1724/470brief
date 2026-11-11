"""Core domain entities for Form 470 requests. Pure Python, no framework imports."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import StrEnum

from brief470.domain.redaction import redact_contact_info


class ServiceCategory(StrEnum):
    C1 = "Category 1"
    C2 = "Category 2"

    @classmethod
    def parse(cls, value: str | None) -> ServiceCategory | None:
        if not value:
            return None
        text = value.strip().lower()
        if text in {"category 1", "c1", "1"}:
            return cls.C1
        if text in {"category 2", "c2", "2"}:
            return cls.C2
        return None

    @property
    def short(self) -> str:
        return "C1" if self is ServiceCategory.C1 else "C2"


@dataclass(frozen=True, slots=True)
class Contact:
    name: str | None = None
    email: str | None = None
    phone: str | None = None

    @property
    def is_empty(self) -> bool:
        return not (self.name or self.email or self.phone)


@dataclass(frozen=True, slots=True)
class ServiceRequest:
    id: str
    category: ServiceCategory | None = None
    service_type: str | None = None
    function: str | None = None
    quantity: str | None = None
    unit: str | None = None
    manufacturer: str | None = None
    description: str | None = None
    rfp_document_urls: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Form470:
    """One certified FCC Form 470 (an application). It holds many service requests."""

    number: str
    funding_year: str
    entity_name: str
    state: str
    city: str | None = None
    applicant_type: str | None = None
    billed_entity_number: str | None = None
    website: str | None = None
    contact: Contact | None = None
    technical_contact: Contact | None = None
    has_consultant: bool = False
    form_pdf_url: str | None = None
    rfp_document_urls: tuple[str, ...] = ()
    certified_at: datetime | None = None
    last_modified_at: datetime | None = None
    allowable_contract_date: date | None = None
    service_requests: tuple[ServiceRequest, ...] = ()

    def is_open(self, today: date) -> bool:
        """True while the allowable contract date (ACD) is today or later.

        The ACD is the earliest date the applicant may sign a contract (28 days after
        certification). It is NOT the bid deadline: each RFP sets its own deadline,
        which is often on or before the ACD. We treat ACD >= today as "still open".
        """
        return self.allowable_contract_date is not None and self.allowable_contract_date >= today

    @property
    def has_equipment(self) -> bool:
        """True when any service request is Category 2 (internal connections, MIBS, BMIC)."""
        return any(sr.category is ServiceCategory.C2 for sr in self.service_requests)

    @property
    def service_types(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for sr in self.service_requests:
            if sr.service_type:
                seen.setdefault(sr.service_type, None)
        return tuple(seen)

    @property
    def categories(self) -> tuple[ServiceCategory, ...]:
        found = {sr.category for sr in self.service_requests if sr.category is not None}
        return tuple(c for c in ServiceCategory if c in found)

    def without_contacts(self) -> Form470:
        """Copy safe for public output: no contact people, emails or phones."""
        requests = tuple(
            replace(sr, description=redact_contact_info(sr.description))
            for sr in self.service_requests
        )
        return replace(self, contact=None, technical_contact=None, service_requests=requests)


@dataclass(frozen=True, slots=True)
class Form470Row:
    """One raw row of the USAC dataset, already typed. One row per RFP attachment."""

    application_number: str
    service_request_id: str
    funding_year: str = ""
    form_version: str | None = None
    status: str | None = None
    allowable_contract_date: date | None = None
    certified_at: datetime | None = None
    last_modified_at: datetime | None = None
    billed_entity_number: str | None = None
    entity_name: str | None = None
    applicant_type: str | None = None
    city: str | None = None
    state: str | None = None
    website: str | None = None
    contact: Contact = field(default_factory=Contact)
    technical_contact: Contact = field(default_factory=Contact)
    consulting_firm_data: str | None = None
    category: ServiceCategory | None = None
    service_type: str | None = None
    function: str | None = None
    quantity: str | None = None
    unit: str | None = None
    manufacturer: str | None = None
    category_two_description: str | None = None
    form_pdf_url: str | None = None
    rfp_document_url: str | None = None


@dataclass(frozen=True, slots=True)
class SyncResult:
    total: int
    open: int
    open_equipment: int
    new: int
    synced_at: datetime
    funding_year: str
    state: str | None = None
