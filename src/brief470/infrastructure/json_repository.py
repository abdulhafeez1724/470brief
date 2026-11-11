"""JSON-file repository. Public snapshot is safe to commit; private one stays local."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

from brief470.domain.entities import (
    Contact,
    Form470,
    ServiceCategory,
    ServiceRequest,
    SyncResult,
)

logger = logging.getLogger(__name__)


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value else None


def _contact_to_dict(c: Contact | None) -> dict[str, Any] | None:
    if c is None or c.is_empty:
        return None
    return {"name": c.name, "email": c.email, "phone": c.phone}


def _contact_from_dict(d: dict[str, Any] | None) -> Contact | None:
    if not d:
        return None
    return Contact(name=d.get("name"), email=d.get("email"), phone=d.get("phone"))


def form_to_dict(form: Form470, include_contacts: bool) -> dict[str, Any]:
    if not include_contacts:
        form = form.without_contacts()
    data: dict[str, Any] = {
        "number": form.number,
        "funding_year": form.funding_year,
        "entity_name": form.entity_name,
        "applicant_type": form.applicant_type,
        "billed_entity_number": form.billed_entity_number,
        "city": form.city,
        "state": form.state,
        "website": form.website,
        "has_consultant": form.has_consultant,
        "form_pdf_url": form.form_pdf_url,
        "rfp_document_urls": list(form.rfp_document_urls),
        "certified_at": _iso(form.certified_at),
        "last_modified_at": _iso(form.last_modified_at),
        "allowable_contract_date": _iso(form.allowable_contract_date),
        "service_requests": [
            {
                "id": sr.id,
                "category": sr.category.value if sr.category else None,
                "service_type": sr.service_type,
                "function": sr.function,
                "quantity": sr.quantity,
                "unit": sr.unit,
                "manufacturer": sr.manufacturer,
                "description": sr.description,
                "rfp_document_urls": list(sr.rfp_document_urls),
            }
            for sr in form.service_requests
        ],
    }
    if include_contacts:
        data["contact"] = _contact_to_dict(form.contact)
        data["technical_contact"] = _contact_to_dict(form.technical_contact)
    return data


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _d(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def form_from_dict(d: dict[str, Any]) -> Form470:
    return Form470(
        number=d["number"],
        funding_year=d.get("funding_year") or "",
        entity_name=d.get("entity_name") or "",
        state=d.get("state") or "",
        city=d.get("city"),
        applicant_type=d.get("applicant_type"),
        billed_entity_number=d.get("billed_entity_number"),
        website=d.get("website"),
        contact=_contact_from_dict(d.get("contact")),
        technical_contact=_contact_from_dict(d.get("technical_contact")),
        has_consultant=bool(d.get("has_consultant")),
        form_pdf_url=d.get("form_pdf_url"),
        rfp_document_urls=tuple(d.get("rfp_document_urls") or ()),
        certified_at=_dt(d.get("certified_at")),
        last_modified_at=_dt(d.get("last_modified_at")),
        allowable_contract_date=_d(d.get("allowable_contract_date")),
        service_requests=tuple(
            ServiceRequest(
                id=sr["id"],
                category=ServiceCategory.parse(sr.get("category")),
                service_type=sr.get("service_type"),
                function=sr.get("function"),
                quantity=sr.get("quantity"),
                unit=sr.get("unit"),
                manufacturer=sr.get("manufacturer"),
                description=sr.get("description"),
                rfp_document_urls=tuple(sr.get("rfp_document_urls") or ()),
            )
            for sr in d.get("service_requests") or ()
        ),
    )


class JsonForm470Repository:
    def __init__(self, public_dir: Path, private_dir: Path) -> None:
        self._public_dir = public_dir
        self._private_dir = private_dir

    def public_path(self, funding_year: str) -> Path:
        return self._public_dir / f"form470_{funding_year}.json"

    def private_path(self, funding_year: str) -> Path:
        return self._private_dir / f"form470_{funding_year}.json"

    @property
    def last_sync_path(self) -> Path:
        return self._public_dir / "last_sync.json"

    # reads -------------------------------------------------------------
    def _read(self, path: Path) -> list[Form470]:
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [form_from_dict(d) for d in payload.get("forms", [])]

    def load(self, funding_year: str) -> list[Form470]:
        private = self.private_path(funding_year)
        return self._read(private if private.exists() else self.public_path(funding_year))

    def load_private(self, funding_year: str) -> list[Form470]:
        return self._read(self.private_path(funding_year))

    def load_last_sync(self) -> SyncResult | None:
        if not self.last_sync_path.exists():
            return None
        d = json.loads(self.last_sync_path.read_text(encoding="utf-8"))
        return SyncResult(
            total=d["total"],
            open=d["open"],
            open_equipment=d["open_equipment"],
            new=d["new"],
            synced_at=datetime.fromisoformat(d["synced_at"]),
            funding_year=d["funding_year"],
            state=d.get("state"),
        )

    # writes ------------------------------------------------------------
    def _write(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(path)
        logger.debug("Wrote %s", path)

    def save_public(self, funding_year: str, forms: Sequence[Form470]) -> None:
        self._write(
            self.public_path(funding_year),
            {
                "funding_year": funding_year,
                "count": len(forms),
                "forms": [form_to_dict(f, include_contacts=False) for f in forms],
            },
        )

    def save_private(self, funding_year: str, forms: Sequence[Form470]) -> None:
        self._write(
            self.private_path(funding_year),
            {
                "funding_year": funding_year,
                "count": len(forms),
                "forms": [form_to_dict(f, include_contacts=True) for f in forms],
            },
        )

    def save_last_sync(self, result: SyncResult) -> None:
        self._write(
            self.last_sync_path,
            {
                "synced_at": result.synced_at.isoformat(timespec="seconds"),
                "funding_year": result.funding_year,
                "state": result.state,
                "total": result.total,
                "open": result.open,
                "open_equipment": result.open_equipment,
                "new": result.new,
            },
        )
