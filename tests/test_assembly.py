from __future__ import annotations

from datetime import date, timedelta

from brief470.domain.assembly import assemble_forms
from brief470.domain.entities import Form470, ServiceCategory, ServiceRequest
from brief470.infrastructure.socrata import Form470RowDto
from tests.conftest import TODAY, raw_row


def _rows(raws: list[dict]) -> list:
    return [Form470RowDto.model_validate(r).to_domain() for r in raws]


def test_dedupe_merges_rfp_urls_per_service_request() -> None:
    a, b = {"url": "https://x/rfp-a.pdf"}, {"url": "https://x/rfp-b.pdf"}
    raws = [
        raw_row(service_request_id="1", rfp_documents=a),
        raw_row(service_request_id="1", rfp_documents=b),
        raw_row(service_request_id="2", service_category="Category 1", rfp_documents=a),
        raw_row(service_request_id="2", service_category="Category 1", rfp_documents=b),
    ]
    forms = assemble_forms(_rows(raws))

    assert len(forms) == 1
    form = forms[0]
    assert [sr.id for sr in form.service_requests] == ["1", "2"]
    for sr in form.service_requests:
        assert sr.rfp_document_urls == ("https://x/rfp-a.pdf", "https://x/rfp-b.pdf")
    assert form.rfp_document_urls == ("https://x/rfp-a.pdf", "https://x/rfp-b.pdf")
    assert form.has_equipment
    assert form.categories == (ServiceCategory.C1, ServiceCategory.C2)
    assert form.has_consultant
    assert form.contact is not None and form.contact.email == "jane.contact@example.org"


def test_duplicate_urls_are_kept_once_in_order() -> None:
    a = {"url": "https://x/a.pdf"}
    raws = [raw_row(rfp_documents=a), raw_row(rfp_documents=a), raw_row(rfp_documents=None)]
    (form,) = assemble_forms(_rows(raws))
    assert form.service_requests[0].rfp_document_urls == ("https://x/a.pdf",)


def test_missing_fields_do_not_crash() -> None:
    raws = [
        {"application_number": "1", "service_request_id": "1"},
        {"application_number": "2"},
        {"application_number": "3", "service_request_id": "1", "allowable_contract_date": "junk"},
        {"application_number": "4", "service_request_id": "1", "form_pdf": "not-an-object"},
        {"application_number": "5", "service_request_id": "1", "quantity": 12},
        {},
    ]
    forms = assemble_forms(_rows(raws))
    assert [f.number for f in forms] == ["1", "2", "3", "4", "5"]
    assert all(f.allowable_contract_date is None for f in forms)
    assert not any(f.is_open(TODAY) for f in forms)
    assert forms[1].service_requests == ()
    assert forms[4].service_requests[0].quantity == "12"


def test_prefers_current_version_rows() -> None:
    raws = [
        raw_row(form_version="Original", service_type="Old type"),
        raw_row(form_version="Current", service_type="Internal Connections"),
    ]
    (form,) = assemble_forms(_rows(raws))
    assert form.service_types == ("Internal Connections",)


def _form(acd: date | None) -> Form470:
    return Form470(
        number="1",
        funding_year="2027",
        entity_name="X",
        state="AZ",
        allowable_contract_date=acd,
        service_requests=(ServiceRequest(id="1", category=ServiceCategory.C1),),
    )


def test_is_open_boundary() -> None:
    assert _form(TODAY).is_open(TODAY)
    assert _form(TODAY + timedelta(days=1)).is_open(TODAY)
    assert not _form(TODAY - timedelta(days=1)).is_open(TODAY)
    assert not _form(None).is_open(TODAY)
    assert not _form(TODAY).has_equipment
