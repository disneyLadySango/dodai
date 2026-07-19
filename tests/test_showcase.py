from __future__ import annotations

from io import BytesIO
from pathlib import Path
from shutil import copytree
from urllib.parse import urlencode

from dodai.showcase import create_showcase_application


def showcase_project(project: Path) -> Path:
    repository_root = Path(__file__).parents[1]
    copytree(repository_root / "projections", project / "projections")
    copytree(repository_root / ".dodai/cache", project / ".dodai/cache")
    copytree(repository_root / "examples", project / "examples")
    return project


def request(application, path: str = "/", method: str = "GET", email: str = "") -> tuple[str, str]:
    values = {"email": email} if email else {"scenario": "guardrail"}
    payload = urlencode(values).encode() if method == "POST" else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(payload)),
        "wsgi.input": BytesIO(payload),
    }
    response: dict[str, str] = {}

    def start_response(status, headers):
        response["status"] = status

    body = b"".join(application(environ, start_response)).decode()
    return response["status"], body


def test_showcase_explains_the_repository_backed_lineage(project: Path) -> None:
    application = create_showcase_application(showcase_project(project))

    status, page = request(application)

    assert status == "200 OK"
    assert "From intent to evidence" in page
    assert "4 origin layers" in page
    assert "GPT-5.6" in page
    assert "Developer projection" in page
    assert "Stakeholder projection" in page


def test_showcase_demonstrates_guardrail_without_mutating_origin(project: Path) -> None:
    application = create_showcase_application(showcase_project(project))
    story_path = project / "origin/02-user-stories.yaml"
    before = story_path.read_bytes()

    status, page = request(application, "/guardrail", "POST")

    assert status == "200 OK"
    assert "Guardrail breached" in page
    assert "revise test specifications" in page.lower()
    assert "spec_regeneration_budget_" in page
    assert story_path.read_bytes() == before


def test_showcase_serves_the_generated_projection(project: Path) -> None:
    application = create_showcase_application(showcase_project(project))

    status, page = request(application, "/projection")

    assert status == "200 OK"
    assert "One origin. Every projection. Less drift." in page
    assert 'action="/projection"' in page

    status, page = request(application, "/projection", "POST", "judge@example.com")
    assert status == "201 Created"
    assert "on the list" in page
