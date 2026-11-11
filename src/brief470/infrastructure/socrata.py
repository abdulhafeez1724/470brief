"""USAC open data (Socrata SoQL) client, API DTOs and source adapters."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, field_validator

from brief470.domain.entities import Contact, Form470Row, ServiceCategory
from brief470.domain.vendors import Vendor

logger = logging.getLogger(__name__)

FORM470_FIELDS: tuple[str, ...] = (
    "application_number", "service_request_id", "form_version", "funding_year",
    "fcc_form_470_status", "allowable_contract_date", "certified_date_time",
    "last_modified_date_time", "billed_entity_number", "billed_entity_name", "applicant_type",
    "billed_entity_city", "billed_entity_state", "website_url", "contact_name", "contact_email",
    "contact_phone", "technical_contact_name", "technical_contact_email", "consulting_firm_data",
    "service_category", "service_type", "function", "quantity", "unit", "manufacturer",
    "category_two_description", "form_pdf", "rfp_documents", "rfp_upload_date",
)  # fmt: skip

VENDOR_FIELDS: tuple[str, ...] = (
    "spin", "service_provider_name", "status", "general_contact_name", "general_contact_email",
    "phone_number", "physical_city", "physical_state", "fcc_form_499_filer",
    "fcc_form_473_spac_filed",
)  # fmt: skip


def _soql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_datetime(value: Any) -> datetime | None:
    text = _clean(value)
    if text is None:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        logger.debug("Unparseable date %r", text)
        return None


class UrlObject(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: str | None = None


class _Dto(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def _empty_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return value


class Form470RowDto(_Dto):
    application_number: str | None = None
    service_request_id: str | None = None
    form_version: str | None = None
    funding_year: str | None = None
    fcc_form_470_status: str | None = None
    allowable_contract_date: datetime | None = None
    certified_date_time: datetime | None = None
    last_modified_date_time: datetime | None = None
    billed_entity_number: str | None = None
    billed_entity_name: str | None = None
    applicant_type: str | None = None
    billed_entity_city: str | None = None
    billed_entity_state: str | None = None
    website_url: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    technical_contact_name: str | None = None
    technical_contact_email: str | None = None
    consulting_firm_data: str | None = None
    service_category: str | None = None
    service_type: str | None = None
    function: str | None = None
    quantity: str | None = None
    unit: str | None = None
    manufacturer: str | None = None
    category_two_description: str | None = None
    form_pdf: UrlObject | None = None
    rfp_documents: UrlObject | None = None
    rfp_upload_date: datetime | None = None

    @field_validator(
        "allowable_contract_date",
        "certified_date_time",
        "last_modified_date_time",
        "rfp_upload_date",
        mode="before",
    )
    @classmethod
    def _dates(cls, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        return _parse_datetime(value)

    @field_validator("form_pdf", "rfp_documents", mode="before")
    @classmethod
    def _url_obj(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"url": value}
        return value if isinstance(value, dict) else None

    def to_domain(self) -> Form470Row:
        acd: date | None = (
            self.allowable_contract_date.date() if self.allowable_contract_date else None
        )
        return Form470Row(
            application_number=self.application_number or "",
            service_request_id=self.service_request_id or "",
            funding_year=self.funding_year or "",
            form_version=self.form_version,
            status=self.fcc_form_470_status,
            allowable_contract_date=acd,
            certified_at=self.certified_date_time,
            last_modified_at=self.last_modified_date_time,
            billed_entity_number=self.billed_entity_number,
            entity_name=self.billed_entity_name,
            applicant_type=self.applicant_type,
            city=self.billed_entity_city,
            state=self.billed_entity_state,
            website=self.website_url,
            contact=Contact(self.contact_name, self.contact_email, self.contact_phone),
            technical_contact=Contact(self.technical_contact_name, self.technical_contact_email),
            consulting_firm_data=self.consulting_firm_data,
            category=ServiceCategory.parse(self.service_category),
            service_type=self.service_type,
            function=self.function,
            quantity=self.quantity,
            unit=self.unit,
            manufacturer=self.manufacturer,
            category_two_description=self.category_two_description,
            form_pdf_url=_clean(self.form_pdf.url) if self.form_pdf else None,
            rfp_document_url=_clean(self.rfp_documents.url) if self.rfp_documents else None,
        )


class VendorDto(_Dto):
    spin: str | None = None
    service_provider_name: str | None = None
    status: str | None = None
    general_contact_name: str | None = None
    general_contact_email: str | None = None
    phone_number: str | None = None
    physical_city: str | None = None
    physical_state: str | None = None
    fcc_form_499_filer: str | None = None
    fcc_form_473_spac_filed: str | None = None

    def to_domain(self) -> Vendor:
        return Vendor(
            spin=self.spin or "",
            name=self.service_provider_name or "",
            status=self.status,
            contact_name=self.general_contact_name,
            contact_email=self.general_contact_email,
            phone=self.phone_number,
            city=self.physical_city,
            state=self.physical_state,
            form_499_filer=self.fcc_form_499_filer,
            spac_years=Vendor.parse_years(self.fcc_form_473_spac_filed),
        )


class SocrataClient:
    """Pages through a Socrata resource with $limit/$offset until a short page."""

    def __init__(
        self,
        http: httpx.AsyncClient,
        base_url: str,
        user_agent: str,
        app_token: str | None = None,
        page_size: int = 5000,
    ) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")
        self._headers = {"User-Agent": user_agent, "Accept": "application/json"}
        if app_token:
            self._headers["X-App-Token"] = app_token
        self._page_size = page_size

    async def fetch_all(
        self, dataset: str, select: tuple[str, ...], where: str, order: str = ":id"
    ) -> list[dict[str, Any]]:
        url = f"{self._base_url}/{dataset}.json"
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            params = {
                "$select": ",".join(select),
                "$where": where,
                "$order": order,
                "$limit": str(self._page_size),
                "$offset": str(offset),
            }
            response = await self._http.get(url, params=params, headers=self._headers)
            response.raise_for_status()
            page = response.json()
            if not isinstance(page, list):
                raise ValueError(f"Unexpected Socrata response for {dataset}: {page!r:.200}")
            rows.extend(page)
            logger.debug("%s offset=%d got=%d", dataset, offset, len(page))
            if len(page) < self._page_size:
                return rows
            offset += self._page_size


class SocrataForm470Source:
    def __init__(self, client: SocrataClient, dataset: str = "jt8s-3q52") -> None:
        self._client = client
        self._dataset = dataset

    async def fetch(self, funding_year: str, state: str | None = None) -> list[Form470Row]:
        where = (
            f"funding_year={_soql_literal(funding_year)} "
            f"AND fcc_form_470_status={_soql_literal('Certified')}"
        )
        if state:
            where += f" AND billed_entity_state={_soql_literal(state.upper())}"
        raw = await self._client.fetch_all(self._dataset, FORM470_FIELDS, where)
        return [Form470RowDto.model_validate(r).to_domain() for r in raw]


class SocrataVendorSource:
    def __init__(self, client: SocrataClient, dataset: str = "xcy2-bdid") -> None:
        self._client = client
        self._dataset = dataset

    async def fetch(self, state: str) -> list[Vendor]:
        where = (
            f"status={_soql_literal('Active')} "
            f"AND physical_state={_soql_literal(state.upper())} "
            f"AND fcc_form_499_filer={_soql_literal('No')}"
        )
        raw = await self._client.fetch_all(self._dataset, VENDOR_FIELDS, where)
        return [VendorDto.model_validate(r).to_domain() for r in raw]
