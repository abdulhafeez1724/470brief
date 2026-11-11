"""Typer CLI and composition root."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Annotated

import httpx
import typer

from brief470.application import (
    BuildStatePages,
    ExportOutreachCsv,
    ExportVendors,
    NoPrivateDataError,
    SyncForm470,
    VendorExportResult,
)
from brief470.domain.entities import SyncResult
from brief470.infrastructure.clock import SystemClock
from brief470.infrastructure.csv_writer import CsvTableWriter
from brief470.infrastructure.json_repository import JsonForm470Repository
from brief470.infrastructure.settings import Settings
from brief470.infrastructure.socrata import SocrataClient, SocrataForm470Source, SocrataVendorSource
from brief470.presentation.renderer import JinjaSiteRenderer

logger = logging.getLogger("brief470")
app = typer.Typer(
    help="470 Brief: E-Rate Form 470 sync, state pages and exports.", no_args_is_help=True
)


StateOpt = Annotated[str | None, typer.Option("--state", help="Two-letter state code, e.g. AZ.")]
StateReq = Annotated[str, typer.Option("--state", help="Two-letter state code, e.g. AZ.")]
YearOpt = Annotated[
    str | None, typer.Option("--year", help="Funding year (default from settings).")
]


@app.callback()
def main(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)


def _settings(year: str | None = None) -> Settings:
    return Settings(funding_year=year) if year else Settings()


def _repo(settings: Settings) -> JsonForm470Repository:
    return JsonForm470Repository(settings.public_dir, settings.private_dir)


def _clock(settings: Settings) -> SystemClock:
    return SystemClock(settings.timezone)


async def _with_client[T](settings: Settings, fn: Callable[[SocrataClient], Awaitable[T]]) -> T:
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as http:
        client = SocrataClient(
            http,
            settings.socrata_base_url,
            settings.user_agent,
            settings.socrata_app_token,
            settings.page_size,
        )
        return await fn(client)


def _run_sync(settings: Settings, state: str | None) -> SyncResult:
    async def go(client: SocrataClient) -> SyncResult:
        use_case = SyncForm470(
            SocrataForm470Source(client, settings.form470_dataset),
            _repo(settings),
            _clock(settings),
            write_private=settings.write_private,
        )
        return await use_case.execute(settings.funding_year, state)

    result = asyncio.run(_with_client(settings, go))
    logger.info(
        "sync FY%s %s: total=%d open=%d open_equipment=%d new=%d",
        result.funding_year,
        result.state or "all states",
        result.total,
        result.open,
        result.open_equipment,
        result.new,
    )
    return result


def _run_build(settings: Settings) -> None:
    renderer = JinjaSiteRenderer(
        settings.site_dir,
        form_url=settings.google_form_url,
        base_url=settings.site_base_url,
        footer_name=settings.footer_name,
    )
    result = BuildStatePages(_repo(settings), renderer, _clock(settings)).execute(
        settings.funding_year
    )
    logger.info(
        "build-pages FY%s: %d state pages + index in %s/states",
        settings.funding_year,
        result.states,
        settings.site_dir,
    )


@app.command()
def sync(state: StateOpt = None, year: YearOpt = None) -> None:
    """Fetch certified Form 470s from USAC open data and save snapshots."""
    _run_sync(_settings(year), state)


@app.command("build-pages")
def build_pages(year: YearOpt = None) -> None:
    """Render site/states/<xx>.html and site/states/index.html from the snapshot."""
    _run_build(_settings(year))


@app.command()
def export(state: StateReq, year: YearOpt = None) -> None:
    """Write a local outreach CSV (with contacts) of open requests for a state."""
    settings = _settings(year)
    use_case = ExportOutreachCsv(
        _repo(settings), CsvTableWriter(settings.private_dir), _clock(settings)
    )
    try:
        result = use_case.execute(settings.funding_year, state)
    except NoPrivateDataError as exc:
        logger.error("%s", exc)
        raise typer.Exit(code=1) from exc
    logger.info("export %s: %d open requests -> %s", state.upper(), result.rows, result.path)


@app.command()
def vendors(state: StateReq) -> None:
    """Write a local CSV of active E-Rate vendors in a state, with review flags."""
    settings = _settings()

    async def go(client: SocrataClient) -> VendorExportResult:
        use_case = ExportVendors(
            SocrataVendorSource(client, settings.vendor_dataset),
            CsvTableWriter(settings.private_dir),
            _clock(settings),
        )
        return await use_case.execute(state)

    result = asyncio.run(_with_client(settings, go))
    logger.info(
        "vendors %s: %d vendors, %d flagged needs_review -> %s",
        state.upper(),
        result.vendors,
        result.flagged,
        result.path,
    )


@app.command("all")
def run_all(state: StateOpt = None, year: YearOpt = None) -> None:
    """sync + build-pages."""
    settings = _settings(year)
    _run_sync(settings, state)
    _run_build(settings)


if __name__ == "__main__":
    app()
