"""Jinja2 renderer that writes the static state pages into site/states/."""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from brief470.domain.pages import StatePage, StatesIndex

logger = logging.getLogger(__name__)

_KEEP_UPPER = {
    "ISD", "USD", "CISD", "CUSD", "UHSD", "ESD", "SD", "CSD", "UFSD", "BOCES", "ESC", "RESA",
    "ESU", "CCSD", "STEM", "STEAM", "LLC", "II", "III", "IV", "VI", "VII", "VIII", "IX", "XI",
    "K-8", "K-12", "PK-8", "USA", "YMCA", "KIPP", "IDEA", "ACE", "AZ", "NYC", "LA",
}  # fmt: skip
_SMALL = {"of", "the", "and", "for", "at", "in", "on", "a", "an", "de", "la", "del"}


def nice_entity(name: str) -> str:
    """Turn ALL-CAPS USAC names into readable title case. Mixed-case names are kept."""
    if not name or not name.isupper():
        return name
    words = re.split(r"(\s+)", name)
    out: list[str] = []
    for i, word in enumerate(words):
        if word.isspace() or not word:
            out.append(word)
            continue
        if word in _KEEP_UPPER or any(ch.isdigit() for ch in word):
            out.append(word)
        elif i > 0 and word.lower() in _SMALL:
            out.append(word.lower())
        else:
            out.append("-".join(part.capitalize() for part in word.split("-")))
    return "".join(out)


def short_date(value: date | None) -> str:
    return f"{value:%b} {value.day}, {value.year}" if value else "Not stated"


def long_date(value: date) -> str:
    return f"{value:%B} {value.day}, {value.year}"


def build_environment() -> Environment:
    env = Environment(
        loader=PackageLoader("brief470.presentation", "templates"),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["entity"] = nice_entity
    env.filters["shortdate"] = short_date
    env.filters["longdate"] = long_date
    return env


class JinjaSiteRenderer:
    def __init__(
        self,
        site_dir: Path,
        form_url: str,
        base_url: str,
        footer_name: str,
    ) -> None:
        self._states_dir = site_dir / "states"
        self._env = build_environment()
        self._common = {"form_url": form_url, "footer_name": footer_name}
        self._base_url = base_url

    def render_state_page(self, page: StatePage) -> str:
        title = (
            f"{page.name} E-Rate Form 470 requests open for bids, "
            f"funding year {page.funding_year} | 470 Brief"
        )
        description = (
            f"{page.open} open E-Rate Form 470 requests from {page.name} schools and libraries "
            f"for funding year {page.funding_year}, {page.open_equipment} with network equipment. "
            f"Updated {long_date(page.updated)} from public USAC data."
        )
        return self._env.get_template("state.html").render(
            page=page,
            title=title,
            description=description,
            canonical=f"{self._base_url}states/{page.code.lower()}.html",
            **self._common,
        )

    def render_states_index(self, index: StatesIndex) -> str:
        total_open = sum(s.open for s in index.states)
        title = f"Open E-Rate requests by state, funding year {index.funding_year} | 470 Brief"
        description = (
            f"{total_open} open E-Rate Form 470 requests across {len(index.states)} states for "
            f"funding year {index.funding_year}. Updated {long_date(index.updated)} from public "
            "USAC data."
        )
        return self._env.get_template("states_index.html").render(
            index=index,
            title=title,
            description=description,
            canonical=f"{self._base_url}states/index.html",
            **self._common,
        )

    def _write(self, name: str, html: str) -> str:
        self._states_dir.mkdir(parents=True, exist_ok=True)
        path = self._states_dir / name
        path.write_text(html, encoding="utf-8")
        return str(path)

    def write_state_page(self, page: StatePage) -> str:
        return self._write(f"{page.code.lower()}.html", self.render_state_page(page))

    def write_states_index(self, index: StatesIndex) -> str:
        return self._write("index.html", self.render_states_index(index))
