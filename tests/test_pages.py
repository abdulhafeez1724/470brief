from __future__ import annotations

from pathlib import Path

from brief470.application import BuildStatePages, SyncForm470
from brief470.infrastructure.json_repository import JsonForm470Repository
from brief470.presentation.renderer import JinjaSiteRenderer, nice_entity
from tests.conftest import FixedClock, raw_row
from tests.test_sync_and_snapshot import FakeSource


async def test_state_page_renders_without_at_sign(
    repo: JsonForm470Repository, clock: FixedClock, tmp_path: Path
) -> None:
    raws = [
        raw_row(application_number="A1"),
        raw_row(
            application_number="A2",
            billed_entity_name="ALPHA SCHOOL",
            service_category="Category 1",
            service_type="Data Transmission and/or Internet Access",
            allowable_contract_date="2026-11-11T00:00:00.000",
        ),
        raw_row(application_number="A3", allowable_contract_date="2026-10-01T00:00:00.000"),
    ]
    # Private snapshot (with contacts) exists: pages must still be contact-free.
    await SyncForm470(FakeSource(raws), repo, clock).execute("2027")

    site = tmp_path / "site"
    renderer = JinjaSiteRenderer(
        site, "https://forms.example/x", "https://ex.github.io/r/", "Owner"
    )
    result = BuildStatePages(repo, renderer, clock).execute("2027")

    assert result.states == 1
    page = (site / "states" / "az.html").read_text()
    index = (site / "states" / "index.html").read_text()
    for html in (page, index):
        assert "@" not in html
        assert "Jane Contact" not in html and "623-933-3733" not in html
        assert "<title>" in html and 'name="description"' in html
        assert "not affiliated with USAC or the FCC" in html

    assert "Arizona: open E-Rate requests, funding year 2027" in page
    assert "Updated November 11, 2026" in page
    assert "<strong>3</strong><span>filed</span>" in page
    assert "<strong>2</strong><span>open</span>" in page
    assert "<strong>1</strong><span>open with equipment</span>" in page
    assert 'scope="col"' in page and 'scope="row"' in page
    assert "Get a one-page brief for any of these" in page
    assert "https://forms.example/x" in page
    # Equipment first even though its contract date is later.
    assert page.index("Pioneer Preparatory School") < page.index("Alpha School")
    assert "#A3" not in page  # closed
    assert 'href="az.html"' in index


def test_nice_entity() -> None:
    assert nice_entity("LAVEEN ELEMENTARY DISTRICT 59") == "Laveen Elementary District 59"
    assert nice_entity("TOWN OF GILBERT USD") == "Town of Gilbert USD"
    assert nice_entity("Already Mixed Case") == "Already Mixed Case"
