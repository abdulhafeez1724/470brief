from __future__ import annotations

import logging

from brief470.domain.assembly import assemble_forms
from brief470.domain.entities import Form470, SyncResult
from brief470.domain.ports import Clock, Form470Repository, Form470Source

logger = logging.getLogger(__name__)


def _merge(existing: list[Form470], fresh: list[Form470], state: str | None) -> list[Form470]:
    """A state-scoped sync replaces that state's records and keeps every other state."""
    if state is None:
        return sorted(fresh, key=lambda f: f.number)
    kept = [f for f in existing if f.state != state]
    return sorted([*kept, *fresh], key=lambda f: f.number)


class SyncForm470:
    def __init__(
        self,
        source: Form470Source,
        repo: Form470Repository,
        clock: Clock,
        write_private: bool = True,
    ) -> None:
        self._source = source
        self._repo = repo
        self._clock = clock
        self._write_private = write_private

    async def execute(self, funding_year: str, state: str | None = None) -> SyncResult:
        state = state.upper() if state else None
        rows = await self._source.fetch(funding_year, state)
        fresh = assemble_forms(rows)
        if state:
            fresh = [f for f in fresh if f.state == state]
        logger.debug("Fetched %d rows -> %d applications", len(rows), len(fresh))

        previous = self._repo.load(funding_year)
        previous_numbers = {f.number for f in previous if state is None or f.state == state}

        self._repo.save_public(funding_year, _merge(previous, fresh, state))
        if self._write_private:
            private_prev = self._repo.load_private(funding_year)
            self._repo.save_private(funding_year, _merge(private_prev, fresh, state))

        today = self._clock.today()
        open_forms = [f for f in fresh if f.is_open(today)]
        result = SyncResult(
            total=len(fresh),
            open=len(open_forms),
            open_equipment=sum(1 for f in open_forms if f.has_equipment),
            new=sum(1 for f in fresh if f.number not in previous_numbers),
            synced_at=self._clock.now(),
            funding_year=funding_year,
            state=state,
        )
        self._repo.save_last_sync(result)
        return result
