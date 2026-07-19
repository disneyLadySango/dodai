from pathlib import Path

import pytest
from waitlist import register


def test_registration_survives_a_new_call(tmp_path: Path) -> None:
    records = tmp_path / "registrations.json"
    assert register("Person@example.com", records) is True
    assert register("person@example.com", records) is False


def test_invalid_email_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="valid email"):
        register("not-an-email", tmp_path / "registrations.json")
