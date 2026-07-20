from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_LANGUAGES = ("ja", "en")


def select_language(value: str | None) -> str:
    return value if value in SUPPORTED_LANGUAGES else "ja"


@lru_cache(maxsize=1)
def japanese_catalog() -> dict[str, Any]:
    path = Path(__file__).parent / "locales" / "ja.yaml"
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Japanese language definition must be a mapping.")
    return value


def translated_record(record_id: str) -> str:
    records = japanese_catalog().get("records", {})
    value = records.get(record_id)
    if not isinstance(value, str):
        raise ValueError(f"Japanese language definition is missing origin record: {record_id}")
    return value
