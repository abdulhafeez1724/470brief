from __future__ import annotations

import csv
from pathlib import Path

from brief470.application import ExportVendors
from brief470.domain.vendors import Vendor, is_candidate_vendor, review_vendor
from tests.conftest import FixedClock


def _v(**kw: object) -> Vendor:
    base: dict[str, object] = {
        "spin": "143000001",
        "name": "Desert Networks LLC",
        "status": "Active",
        "contact_email": "pat@desertnetworks.com",
        "state": "AZ",
        "form_499_filer": "No",
        "spac_years": (2024, 2025, 2026),
    }
    base.update(kw)
    return Vendor(**base)  # type: ignore[arg-type]


def test_candidate_filter() -> None:
    assert is_candidate_vendor(_v(), "AZ", 2026)
    assert not is_candidate_vendor(_v(status="Inactive"), "AZ", 2026)
    assert not is_candidate_vendor(_v(state="NM"), "AZ", 2026)
    assert not is_candidate_vendor(_v(form_499_filer="Yes"), "AZ", 2026)
    assert not is_candidate_vendor(_v(spac_years=(2024, 2025)), "AZ", 2026)
    assert not is_candidate_vendor(_v(spac_years=()), "AZ", 2026)


def test_parse_years() -> None:
    assert Vendor.parse_years("2024, 2025,2026") == (2024, 2025, 2026)
    assert Vendor.parse_years(None) == ()
    assert Vendor.parse_years("x,2025") == (2025,)


def test_needs_review_flags() -> None:
    assert not review_vendor(_v()).needs_review
    for name in ("Maricopa County", "City of Mesa", "Mesa School Supply", "Board of Regents"):
        r = review_vendor(_v(name=name))
        assert r.needs_review and "name contains" in r.reason
    for email in ("usac@x.com", "erate@x.com", "sales@x.com", "info@x.com", "compliance@x.com"):
        r = review_vendor(_v(contact_email=email))
        assert r.needs_review and "generic email" in r.reason
    for email in ("bob@gmail.com", "bob@yahoo.com", "bob@juno.com"):
        r = review_vendor(_v(contact_email=email))
        assert r.needs_review and "free-mail" in r.reason
    both = review_vendor(_v(name="Town of Gilbert", contact_email="info@gmail.com"))
    assert both.reason.count(";") == 2


class FakeVendorSource:
    async def fetch(self, state: str) -> list[Vendor]:
        return [
            _v(spin="1", name="Zeta Wireless"),
            _v(spin="2", name="Alpha Electric Association"),
            _v(spin="3", name="Old Co", spac_years=(2019,)),
        ]


async def test_export_vendors(tmp_path: Path) -> None:
    from brief470.infrastructure.csv_writer import CsvTableWriter

    result = await ExportVendors(
        FakeVendorSource(), CsvTableWriter(tmp_path), FixedClock()
    ).execute("az")
    assert (result.vendors, result.flagged) == (2, 1)
    rows = list(csv.DictReader((tmp_path / "vendors" / "AZ.csv").open()))
    assert [r["service_provider_name"] for r in rows] == [
        "Alpha Electric Association",
        "Zeta Wireless",
    ]
    assert rows[0]["needs_review"] == "yes"
