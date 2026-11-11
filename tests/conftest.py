from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from brief470.infrastructure.json_repository import JsonForm470Repository

TODAY = date(2026, 11, 11)


class FixedClock:
    def __init__(self, today: date = TODAY) -> None:
        self._today = today

    def now(self) -> datetime:
        return datetime(self._today.year, self._today.month, self._today.day, 4, 17)

    def today(self) -> date:
        return self._today


def raw_row(**overrides: Any) -> dict[str, Any]:
    """A realistic raw USAC Form 470 row (one per RFP attachment)."""
    row: dict[str, Any] = {
        "application_number": "270001384",
        "service_request_id": "1",
        "form_version": "Current",
        "funding_year": "2027",
        "fcc_form_470_status": "Certified",
        "allowable_contract_date": "2026-12-04T00:00:00.000",
        "certified_date_time": "2026-11-06T11:39:49.000",
        "last_modified_date_time": "2026-11-07T11:54:52.000",
        "billed_entity_number": "16060249",
        "billed_entity_name": "PIONEER PREPARATORY SCHOOL",
        "applicant_type": "School",
        "billed_entity_city": "PHOENIX",
        "billed_entity_state": "AZ",
        "website_url": "https://example.org",
        "contact_name": "Jane Contact",
        "contact_email": "jane.contact@example.org",
        "contact_phone": "623-933-3733",
        "technical_contact_name": "Tom Tech",
        "technical_contact_email": "tom.tech@example.org",
        "consulting_firm_data": "{Nexus E-Rate |17027114|602-799-2639|info@nexus.example}",
        "service_category": "Category 2",
        "service_type": "Internal Connections",
        "function": "Wireless Access Points",
        "quantity": "25",
        "unit": "Each",
        "manufacturer": "Ubiquiti",
        "category_two_description": "Send bids to jane.contact@example.org or call 623-933-3733.",
        "form_pdf": {"url": "https://publicdata.usac.org/form.pdf"},
        "rfp_documents": {"url": "https://publicdata.usac.org/rfp-a.pdf"},
        "rfp_upload_date": "2026-11-06T11:10:50.000",
    }
    row.update(overrides)
    return row


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def repo(tmp_path: Path) -> JsonForm470Repository:
    return JsonForm470Repository(tmp_path / "public", tmp_path / "private")
