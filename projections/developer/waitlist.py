"""Generated waitlist projection. Regenerate instead of editing."""

from __future__ import annotations

import json
import re
from pathlib import Path

PRODUCT_NAME = "dodai"
HEADLINE = "One origin. Every projection. Less drift."
VALUE_PROPOSITION = (
    "Keep product intent authoritative while producing consistent developer "
    + "and stakeholder projections—without repeatedly translating intent or "
    + "directing technical methods."
)
CALL_TO_ACTION = "Join the waitlist"


def register(email: str, records_path: Path) -> bool:
    normalized = email.strip().lower()
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized) is None:
        raise ValueError("Enter a valid email address.")
    records = json.loads(records_path.read_text()) if records_path.exists() else []
    if normalized in records:
        return False
    records.append(normalized)
    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text(json.dumps(records, indent=2) + "\n")
    return True
