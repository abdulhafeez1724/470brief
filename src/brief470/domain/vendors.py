"""E-Rate service providers (vendors) and the rules for picking real, active ones."""

from __future__ import annotations

from dataclasses import dataclass

NON_VENDOR_NAME_MARKERS: tuple[str, ...] = (
    "County",
    "City of",
    "Town of",
    "School",
    "District",
    "University",
    "Board of",
    "Regents",
    "Consortium",
    "Utilities",
    "Electric Association",
)
GENERIC_EMAIL_PREFIXES: tuple[str, ...] = ("usac@", "erate@", "sales@", "info@", "compliance@")
FREE_MAIL_DOMAINS: tuple[str, ...] = ("gmail", "yahoo", "juno")


@dataclass(frozen=True, slots=True)
class Vendor:
    spin: str
    name: str
    status: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    phone: str | None = None
    city: str | None = None
    state: str | None = None
    form_499_filer: str | None = None
    spac_years: tuple[int, ...] = ()

    @staticmethod
    def parse_years(raw: str | None) -> tuple[int, ...]:
        if not raw:
            return ()
        years: list[int] = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                years.append(int(part))
        return tuple(years)


@dataclass(frozen=True, slots=True)
class VendorReview:
    vendor: Vendor
    needs_review: bool
    reason: str


def is_candidate_vendor(vendor: Vendor, state: str, year: int) -> bool:
    """Active, in the state, not a 499 filer (i.e. not a telecom carrier), SPAC filed this year."""
    return (
        (vendor.status or "").strip().lower() == "active"
        and (vendor.state or "").strip().upper() == state.strip().upper()
        and (vendor.form_499_filer or "").strip().lower() == "no"
        and year in vendor.spac_years
    )


def review_vendor(vendor: Vendor) -> VendorReview:
    reasons: list[str] = []
    name = vendor.name or ""
    lowered_name = name.lower()
    for marker in NON_VENDOR_NAME_MARKERS:
        if marker.lower() in lowered_name:
            reasons.append(f"name contains '{marker}'")
            break

    email = (vendor.contact_email or "").strip().lower()
    if email:
        for prefix in GENERIC_EMAIL_PREFIXES:
            if email.startswith(prefix):
                reasons.append(f"generic email '{prefix}'")
                break
        domain = email.rsplit("@", 1)[-1] if "@" in email else ""
        for free in FREE_MAIL_DOMAINS:
            if domain == free or domain.startswith(f"{free}."):
                reasons.append(f"free-mail domain '{free}'")
                break

    return VendorReview(vendor=vendor, needs_review=bool(reasons), reason="; ".join(reasons))
