from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    funding_year: str = "2027"
    socrata_app_token: str | None = None
    socrata_base_url: str = "https://opendata.usac.org/resource"
    form470_dataset: str = "jt8s-3q52"
    vendor_dataset: str = "xcy2-bdid"
    page_size: int = 5000
    http_timeout_seconds: float = 60.0
    user_agent: str = "470brief/0.1 (+https://github.com/abdulhafeez1724/470brief)"

    data_dir: Path = Path("data")
    site_dir: Path = Path("site")
    # Set WRITE_PRIVATE=false in CI so contact data is never written on shared runners.
    write_private: bool = True
    timezone: str = "America/New_York"

    google_form_url: str = "REPLACE_WITH_GOOGLE_FORM_LINK"
    site_base_url: str = "https://abdulhafeez1724.github.io/470brief/"
    footer_name: str = "Abdul Hafeez"

    @field_validator("funding_year", mode="before")
    @classmethod
    def _year_as_str(cls, value: object) -> str:
        text = str(value).strip()
        if not (text.isdigit() and len(text) == 4):
            raise ValueError("funding_year must be a 4-digit year")
        return text

    @field_validator("socrata_app_token", mode="before")
    @classmethod
    def _blank_token_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("site_base_url")
    @classmethod
    def _trailing_slash(cls, value: str) -> str:
        return value if value.endswith("/") else value + "/"

    @property
    def public_dir(self) -> Path:
        return self.data_dir / "public"

    @property
    def private_dir(self) -> Path:
        return self.data_dir / "private"
