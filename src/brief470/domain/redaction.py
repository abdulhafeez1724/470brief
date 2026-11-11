"""Remove personal contact details from free text before it goes public."""

from __future__ import annotations

import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+\s*@\s*[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Loose US phone pattern: 602-799-2639, (602) 799 2639, 602.799.2639, +1 602 799 2639
PHONE_RE = re.compile(
    r"(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}(?:\s*(?:x|ext\.?)\s*\d+)?"
)
REDACTED = "[redacted]"


def redact_contact_info(text: str | None) -> str | None:
    if text is None:
        return None
    text = EMAIL_RE.sub(REDACTED, text)
    text = PHONE_RE.sub(REDACTED, text)
    # Any stray "@" left (e.g. "name @ domain" variants) is removed too.
    return text.replace("@", " at ")
