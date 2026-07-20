from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode

import pytest
from waitlist import HEADLINE, create_application, register


def request(application, method: str = "GET", email: str = "") -> tuple[str, str]:
    payload = urlencode({"email": email}).encode() if method == "POST" else b""
    environ = {
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(payload)),
        "wsgi.input": BytesIO(payload),
    }
    response = {}

    def start_response(status, headers):
        response["status"] = status

    body = b"".join(application(environ, start_response)).decode()
    return response["status"], body


def test_registration_survives_a_new_call(tmp_path: Path) -> None:
    records = tmp_path / "registrations.json"
    assert register("Person@example.com", records) is True
    assert register("person@example.com", records) is False


def test_invalid_email_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="valid email"):
        register("not-an-email", tmp_path / "registrations.json")


def test_browser_journey_explains_registration_outcomes(tmp_path: Path) -> None:
    application = create_application(tmp_path / "registrations.json")

    status, page = request(application)
    assert status == "200 OK"
    assert HEADLINE in page

    status, page = request(application, "POST", "person@example.com")
    assert status == "201 Created"
    assert "on the list" in page

    status, page = request(application, "POST", "person@example.com")
    assert status == "200 OK"
    assert "already on the list" in page

    status, page = request(application, "POST", "not-an-email")
    assert status == "400 Bad Request"
    assert "valid email" in page
