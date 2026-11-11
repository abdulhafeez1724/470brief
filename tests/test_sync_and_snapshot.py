from __future__ import annotations

import json
import re

from brief470.application import ExportOutreachCsv, ListOpenRequests, SyncForm470
from brief470.domain.entities import Form470Row, ServiceCategory
from brief470.infrastructure.csv_writer import CsvTableWriter
from brief470.infrastructure.json_repository import JsonForm470Repository
from brief470.infrastructure.socrata import Form470RowDto
from tests.conftest import FixedClock, raw_row

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


class FakeSource:
    def __init__(self, raws: list[dict]) -> None:
        self.raws = raws

    async def fetch(self, funding_year: str, state: str | None = None) -> list[Form470Row]:
        return [Form470RowDto.model_validate(r).to_domain() for r in self.raws]


def _raws() -> list[dict]:
    return [
        raw_row(application_number="A1", service_request_id="1"),
        raw_row(
            application_number="A1",
            service_request_id="1",
            rfp_documents={"url": "https://x/b.pdf"},
        ),
        raw_row(
            application_number="A2",
            billed_entity_name="ALPHA SCHOOL",
            service_category="Category 1",
            service_type="Data Transmission and/or Internet Access",
            allowable_contract_date="2026-11-11T00:00:00.000",
        ),
        raw_row(application_number="A3", allowable_contract_date="2026-11-01T00:00:00.000"),
        raw_row(application_number="T1", billed_entity_state="TX"),
    ]


async def test_sync_counts_and_new(repo: JsonForm470Repository, clock: FixedClock) -> None:
    sync = SyncForm470(FakeSource(_raws()), repo, clock)
    first = await sync.execute("2027")
    assert (first.total, first.open, first.open_equipment, first.new) == (4, 3, 2, 4)

    second = await sync.execute("2027")
    assert second.new == 0
    last = repo.load_last_sync()
    assert last is not None and last.total == 4 and last.new == 0


async def test_state_sync_keeps_other_states(
    repo: JsonForm470Repository, clock: FixedClock
) -> None:
    await SyncForm470(FakeSource(_raws()), repo, clock).execute("2027")
    az_only = [r for r in _raws() if r["billed_entity_state"] == "AZ"]
    result = await SyncForm470(FakeSource(az_only), repo, clock).execute("2027", "az")
    assert result.state == "AZ" and result.total == 3
    assert {f.state for f in repo.load("2027")} == {"AZ", "TX"}


async def test_public_snapshot_has_no_contacts(
    repo: JsonForm470Repository, clock: FixedClock
) -> None:
    await SyncForm470(FakeSource(_raws()), repo, clock).execute("2027")
    text = repo.public_path("2027").read_text()

    assert "contact_" not in text
    assert "technical_contact" not in text
    assert '"contact"' not in text
    assert not EMAIL_RE.search(text)
    assert "@" not in text
    assert "623-933-3733" not in text
    assert "Jane Contact" not in text and "Tom Tech" not in text

    payload = json.loads(text)
    assert payload["count"] == 4
    form = next(f for f in payload["forms"] if f["number"] == "A1")
    assert form["service_requests"][0]["rfp_document_urls"] == [
        "https://publicdata.usac.org/rfp-a.pdf",
        "https://x/b.pdf",
    ]

    private = repo.load_private("2027")
    assert private and private[0].contact is not None


async def test_private_not_written_when_disabled(
    repo: JsonForm470Repository, clock: FixedClock
) -> None:
    await SyncForm470(FakeSource(_raws()), repo, clock, write_private=False).execute("2027")
    assert repo.public_path("2027").exists()
    assert not repo.private_path("2027").exists()


async def test_list_open_sorted_and_filtered(
    repo: JsonForm470Repository, clock: FixedClock
) -> None:
    await SyncForm470(FakeSource(_raws()), repo, clock).execute("2027")
    listing = ListOpenRequests(repo, clock)
    az = listing.execute("2027", "AZ")
    assert [f.number for f in az] == ["A2", "A1"]  # Nov 11 before Dec 4
    c2 = listing.execute("2027", "AZ", ServiceCategory.C2)
    assert [f.number for f in c2] == ["A1"]


async def test_export_outreach_csv(
    repo: JsonForm470Repository, clock: FixedClock, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    await SyncForm470(FakeSource(_raws()), repo, clock).execute("2027")
    result = ExportOutreachCsv(repo, CsvTableWriter(tmp_path / "private"), clock).execute(
        "2027", "az"
    )
    assert result.rows == 2
    assert result.path.endswith("exports/AZ_open_2026-11-11.csv")
    content = (tmp_path / "private" / "exports" / "AZ_open_2026-11-11.csv").read_text()
    assert "jane.contact@example.org" in content and "tom.tech@example.org" in content
