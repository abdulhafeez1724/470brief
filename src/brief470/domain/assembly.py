"""Dedupe raw dataset rows into Form470 aggregates.

The USAC dataset has one row per RFP attachment, so a service request repeats once
per document. We group by (application_number, service_request_id) and merge the
document URLs into a unique, ordered list.
"""

from __future__ import annotations

from collections.abc import Iterable

from brief470.domain.entities import (
    Contact,
    Form470,
    Form470Row,
    ServiceCategory,
    ServiceRequest,
)


def _unique(values: Iterable[str | None]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for value in values:
        if value:
            seen.setdefault(value, None)
    return tuple(seen)


def _first(values: Iterable[str | None]) -> str | None:
    return next((v for v in values if v), None)


def _contact(rows: list[Form470Row], technical: bool) -> Contact | None:
    for row in rows:
        c = row.technical_contact if technical else row.contact
        if not c.is_empty:
            return c
    return None


def _prefer_current(rows: list[Form470Row]) -> list[Form470Row]:
    """If an application has both 'Current' and 'Original' rows, keep only 'Current'."""
    current = [r for r in rows if (r.form_version or "").lower() == "current"]
    return current or rows


def assemble_forms(rows: Iterable[Form470Row]) -> list[Form470]:
    by_app: dict[str, list[Form470Row]] = {}
    for row in rows:
        if not row.application_number:
            continue
        by_app.setdefault(row.application_number, []).append(row)

    forms: list[Form470] = []
    for number, app_rows in by_app.items():
        app_rows = _prefer_current(app_rows)
        by_sr: dict[str, list[Form470Row]] = {}
        for row in app_rows:
            by_sr.setdefault(row.service_request_id or "", []).append(row)

        requests: list[ServiceRequest] = []
        for sr_id, sr_rows in by_sr.items():
            if not sr_id:
                continue
            head = sr_rows[0]
            requests.append(
                ServiceRequest(
                    id=sr_id,
                    category=_first_category(sr_rows),
                    service_type=_first(r.service_type for r in sr_rows),
                    function=_first(r.function for r in sr_rows),
                    quantity=_first(r.quantity for r in sr_rows),
                    unit=_first(r.unit for r in sr_rows),
                    manufacturer=_first(r.manufacturer for r in sr_rows),
                    description=head.category_two_description
                    or _first(r.category_two_description for r in sr_rows),
                    rfp_document_urls=_unique(r.rfp_document_url for r in sr_rows),
                )
            )
        requests.sort(key=_sr_sort_key)

        head = app_rows[0]
        forms.append(
            Form470(
                number=number,
                funding_year=_first(r.funding_year for r in app_rows) or "",
                entity_name=_first(r.entity_name for r in app_rows) or f"Form 470 #{number}",
                state=(_first(r.state for r in app_rows) or "").upper(),
                city=_first(r.city for r in app_rows),
                applicant_type=_first(r.applicant_type for r in app_rows),
                billed_entity_number=_first(r.billed_entity_number for r in app_rows),
                website=_first(r.website for r in app_rows),
                contact=_contact(app_rows, technical=False),
                technical_contact=_contact(app_rows, technical=True),
                has_consultant=any((r.consulting_firm_data or "").strip() for r in app_rows),
                form_pdf_url=_first(r.form_pdf_url for r in app_rows),
                rfp_document_urls=_unique(r.rfp_document_url for r in app_rows),
                certified_at=head.certified_at
                or next((r.certified_at for r in app_rows if r.certified_at), None),
                last_modified_at=max(
                    (r.last_modified_at for r in app_rows if r.last_modified_at), default=None
                ),
                allowable_contract_date=next(
                    (r.allowable_contract_date for r in app_rows if r.allowable_contract_date),
                    None,
                ),
                service_requests=tuple(requests),
            )
        )
    forms.sort(key=lambda f: f.number)
    return forms


def _first_category(rows: list[Form470Row]) -> ServiceCategory | None:
    return next((r.category for r in rows if r.category is not None), None)


def _sr_sort_key(sr: ServiceRequest) -> tuple[int, str]:
    return (int(sr.id), "") if sr.id.isdigit() else (10**9, sr.id)
