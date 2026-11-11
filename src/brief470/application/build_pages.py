from __future__ import annotations

from dataclasses import dataclass

from brief470.application.list_open import select_open
from brief470.domain.entities import Form470
from brief470.domain.pages import PageRenderer, StatePage, StatesIndex, StateSummary
from brief470.domain.ports import Clock, Form470Repository
from brief470.domain.states import state_name


@dataclass(frozen=True, slots=True)
class BuildPagesResult:
    states: int
    paths: tuple[str, ...]


class BuildStatePages:
    def __init__(self, repo: Form470Repository, renderer: PageRenderer, clock: Clock) -> None:
        self._repo = repo
        self._renderer = renderer
        self._clock = clock

    def execute(self, funding_year: str) -> BuildPagesResult:
        today = self._clock.today()
        # Always strip contacts here, whichever snapshot the repository returned.
        forms = [f.without_contacts() for f in self._repo.load(funding_year)]

        by_state: dict[str, list[Form470]] = {}
        for form in forms:
            if form.state:
                by_state.setdefault(form.state, []).append(form)

        paths: list[str] = []
        summaries: list[StateSummary] = []
        for code in sorted(by_state):
            state_forms = by_state[code]
            open_forms = select_open(state_forms, today)
            # Equipment (Category 2) requests first, then by contract date and name.
            ordered = sorted(open_forms, key=lambda f: not f.has_equipment)
            page = StatePage(
                code=code,
                name=state_name(code),
                funding_year=funding_year,
                updated=today,
                filed=len(state_forms),
                open=len(open_forms),
                open_equipment=sum(1 for f in open_forms if f.has_equipment),
                requests=tuple(ordered),
            )
            paths.append(self._renderer.write_state_page(page))
            summaries.append(
                StateSummary(code, page.name, page.filed, page.open, page.open_equipment)
            )

        summaries.sort(key=lambda s: s.name)
        index = StatesIndex(funding_year=funding_year, updated=today, states=tuple(summaries))
        paths.append(self._renderer.write_states_index(index))
        return BuildPagesResult(states=len(summaries), paths=tuple(paths))
