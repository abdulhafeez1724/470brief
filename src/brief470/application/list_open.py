from __future__ import annotations

from datetime import date

from brief470.domain.entities import Form470, ServiceCategory
from brief470.domain.ports import Clock, Form470Repository


def open_sort_key(form: Form470) -> tuple[date, str]:
    return (form.allowable_contract_date or date.max, form.entity_name.lower())


def select_open(
    forms: list[Form470],
    today: date,
    state: str | None = None,
    category: ServiceCategory | None = None,
) -> list[Form470]:
    selected = [
        f
        for f in forms
        if f.is_open(today)
        and (state is None or f.state == state.upper())
        and (category is None or category in f.categories)
    ]
    return sorted(selected, key=open_sort_key)


class ListOpenRequests:
    def __init__(self, repo: Form470Repository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock

    def execute(
        self,
        funding_year: str,
        state: str | None = None,
        category: ServiceCategory | None = None,
    ) -> list[Form470]:
        forms = self._repo.load(funding_year)
        return select_open(forms, self._clock.today(), state, category)
