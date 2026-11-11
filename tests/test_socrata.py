from __future__ import annotations

import httpx
import respx

from brief470.infrastructure.socrata import SocrataClient, SocrataForm470Source, SocrataVendorSource
from tests.conftest import raw_row

BASE = "https://opendata.usac.org/resource"


@respx.mock
async def test_pagination_stops_on_short_page() -> None:
    pages = [
        [raw_row(application_number=f"A{i}") for i in range(3)],
        [raw_row(application_number=f"B{i}") for i in range(3)],
        [raw_row(application_number="C0")],
    ]
    seen_offsets: list[str] = []

    def responder(request: httpx.Request) -> httpx.Response:
        offset = request.url.params["$offset"]
        seen_offsets.append(offset)
        return httpx.Response(200, json=pages[int(offset) // 3])

    route = respx.get(f"{BASE}/jt8s-3q52.json").mock(side_effect=responder)
    async with httpx.AsyncClient() as http:
        client = SocrataClient(http, BASE, "470brief-test", app_token="tok", page_size=3)
        rows = await SocrataForm470Source(client).fetch("2027", "az")

    assert len(rows) == 7
    assert seen_offsets == ["0", "3", "6"]
    first = route.calls[0].request
    assert first.headers["X-App-Token"] == "tok"
    assert first.headers["User-Agent"] == "470brief-test"
    where = first.url.params["$where"]
    assert "funding_year='2027'" in where
    assert "fcc_form_470_status='Certified'" in where
    assert "billed_entity_state='AZ'" in where
    assert first.url.params["$limit"] == "3"


@respx.mock
async def test_exact_multiple_page_then_empty_page() -> None:
    calls = {"n": 0}

    def responder(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=[raw_row()] * 2 if calls["n"] == 1 else [])

    respx.get(f"{BASE}/jt8s-3q52.json").mock(side_effect=responder)
    async with httpx.AsyncClient() as http:
        client = SocrataClient(http, BASE, "ua", page_size=2)
        rows = await SocrataForm470Source(client).fetch("2027")
    assert len(rows) == 2 and calls["n"] == 2


@respx.mock
async def test_no_token_header_when_absent_and_vendor_parse() -> None:
    route = respx.get(f"{BASE}/xcy2-bdid.json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "spin": "143034502",
                    "service_provider_name": "Kayenell, Inc.",
                    "status": "Active",
                    "physical_state": "AZ",
                    "fcc_form_499_filer": "No",
                    "fcc_form_473_spac_filed": "2025,2026",
                },
                {"spin": "2"},
            ],
        )
    )
    async with httpx.AsyncClient() as http:
        vendors = await SocrataVendorSource(SocrataClient(http, BASE, "ua")).fetch("AZ")
    assert "X-App-Token" not in route.calls[0].request.headers
    assert vendors[0].spac_years == (2025, 2026)
    assert vendors[1].name == ""
