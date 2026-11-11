from __future__ import annotations

from dataclasses import dataclass

from brief470.domain.ports import Clock, TableWriter, VendorSource
from brief470.domain.vendors import is_candidate_vendor, review_vendor

VENDOR_HEADER: tuple[str, ...] = (
    "spin",
    "service_provider_name",
    "status",
    "general_contact_name",
    "general_contact_email",
    "phone_number",
    "physical_city",
    "physical_state",
    "fcc_form_499_filer",
    "fcc_form_473_spac_filed",
    "needs_review",
    "review_reason",
)


@dataclass(frozen=True, slots=True)
class VendorExportResult:
    path: str
    vendors: int
    flagged: int


class ExportVendors:
    def __init__(self, source: VendorSource, writer: TableWriter, clock: Clock) -> None:
        self._source = source
        self._writer = writer
        self._clock = clock

    async def execute(self, state: str) -> VendorExportResult:
        state = state.upper()
        year = self._clock.today().year
        vendors = [
            v for v in await self._source.fetch(state) if is_candidate_vendor(v, state, year)
        ]
        vendors.sort(key=lambda v: v.name.lower())
        reviews = [review_vendor(v) for v in vendors]
        rows = [
            [
                r.vendor.spin,
                r.vendor.name,
                r.vendor.status or "",
                r.vendor.contact_name or "",
                r.vendor.contact_email or "",
                r.vendor.phone or "",
                r.vendor.city or "",
                r.vendor.state or "",
                r.vendor.form_499_filer or "",
                ",".join(str(y) for y in r.vendor.spac_years),
                "yes" if r.needs_review else "no",
                r.reason,
            ]
            for r in reviews
        ]
        path = self._writer.write(f"vendors/{state}.csv", VENDOR_HEADER, rows)
        return VendorExportResult(
            path=path, vendors=len(rows), flagged=sum(1 for r in reviews if r.needs_review)
        )
