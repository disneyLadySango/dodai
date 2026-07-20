from __future__ import annotations

from io import BytesIO
from pathlib import Path
from shutil import copytree
from urllib.parse import urlencode

import yaml

from dodai.projection import ProjectionContent
from dodai.showcase import create_showcase_application


class WorkbenchProvider:
    def derive(self, origin_text: str) -> ProjectionContent:
        return ProjectionContent(
            product_name="dodai",
            audience="Product teams",
            headline="Govern every change",
            value_proposition="Inspect consequences before approval.",
            call_to_action="Continue",
            stakeholder_summary="One approved change remains connected across roles.",
        )


class FailingWorkbenchProvider:
    def derive(self, origin_text: str) -> ProjectionContent:
        raise RuntimeError("sensitive provider detail")


def showcase_project(project: Path) -> Path:
    repository_root = Path(__file__).parents[1]
    copytree(repository_root / "projections", project / "projections")
    copytree(repository_root / ".dodai/cache", project / ".dodai/cache")
    copytree(repository_root / "examples", project / "examples")
    return project


def request(
    application,
    path: str = "/",
    method: str = "GET",
    email: str = "",
    form: dict[str, str] | None = None,
    query: str = "",
) -> tuple[str, str]:
    values = form or ({"email": email} if email else {"scenario": "guardrail"})
    payload = urlencode(values).encode() if method == "POST" else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(payload)),
        "wsgi.input": BytesIO(payload),
    }
    response: dict[str, str] = {}

    def start_response(status, headers):
        response["status"] = status

    body = b"".join(application(environ, start_response)).decode()
    return response["status"], body


def test_showcase_defaults_to_japanese_and_can_switch_to_english(project: Path) -> None:
    application = create_showcase_application(showcase_project(project))

    status, japanese = request(application)
    english_status, english = request(application, query="lang=en")

    assert status == english_status == "200 OK"
    assert '<html lang="ja">' in japanese
    assert "意図から証拠へ" in japanese
    assert "監査可能な1つの原点" in japanese
    assert "One auditable origin becomes" not in japanese
    assert "プロダクトマネージャーとエンジニア" in japanese
    assert 'href="/?lang=en"' in japanese
    assert '<html lang="en">' in english
    assert "From intent to evidence" in english
    assert 'href="/?lang=ja"' in english


def test_workbench_presents_every_origin_record_in_japanese(project: Path) -> None:
    project = showcase_project(project)
    application = create_showcase_application(project, provider_factory=WorkbenchProvider)

    status, page = request(application, "/workbench")
    expected_ids = []
    for path in sorted((project / "origin").glob("0*.yaml")):
        layer = yaml.safe_load(path.read_text())
        collection = next(
            key for key in ("terms", "stories", "criteria", "specifications") if key in layer
        )
        expected_ids.extend(record["id"] for record in layer[collection])

    assert status == "200 OK"
    assert '<html lang="ja">' in page
    assert "原点ワークベンチ" in page
    assert "意味の監査" in page
    assert page.index("意味の監査") < page.index("Candidate origin text")
    assert "正本の原文を編集する" in page
    for record_id in expected_ids:
        assert f'data-origin-id="{record_id}"' in page


def test_language_choice_does_not_change_candidate_consequences(project: Path) -> None:
    project = showcase_project(project)
    application = create_showcase_application(project, provider_factory=WorkbenchProvider)
    original = (project / "origin/02-user-stories.yaml").read_text()
    proposed = original.replace("revision: 3", "revision: 4", 1).replace(
        "authoritative meaning is unclear.", "authoritative consequences are unclear."
    )

    _, japanese = request(
        application,
        "/candidate",
        "POST",
        form={"layer_file": "02-user-stories.yaml", "proposed_text": proposed, "lang": "ja"},
    )
    _, english = request(
        application,
        "/candidate",
        "POST",
        form={"layer_file": "02-user-stories.yaml", "proposed_text": proposed, "lang": "en"},
    )

    japanese_id = japanese.split('name="candidate_id" value="', 1)[1].split('"', 1)[0]
    english_id = english.split('name="candidate_id" value="', 1)[1].split('"', 1)[0]
    assert japanese_id == english_id
    assert "story_authority_drift" in japanese and "story_authority_drift" in english
    assert "spec_candidate_impact_is_visible" in japanese
    assert "spec_candidate_impact_is_visible" in english


def test_showcase_explains_the_repository_backed_lineage(project: Path) -> None:
    application = create_showcase_application(showcase_project(project))

    status, page = request(application, query="lang=en")

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

    status, page = request(application, "/guardrail", "POST", form={"lang": "en"})

    assert status == "200 OK"
    assert "Guardrail breached" in page
    assert "revise test specifications" in page.lower()
    assert "spec_regeneration_budget_" in page
    assert "Adopt as layer-four verification" in page
    assert story_path.read_bytes() == before


def test_showcase_serves_the_generated_projection(project: Path) -> None:
    project = showcase_project(project)
    application = create_showcase_application(project)
    manifest = yaml.safe_load((project / "projections/manifest.yaml").read_text())
    semantic = yaml.safe_load(
        (project / ".dodai/cache" / f"{manifest['origin_digest']}.yaml").read_text()
    )

    status, page = request(application, "/projection")

    assert status == "200 OK"
    assert semantic["headline"] in page
    assert 'action="/projection"' in page

    status, page = request(application, "/projection", "POST", "judge@example.com")
    assert status == "201 Created"
    assert "on the list" in page


def test_workbench_previews_impact_before_origin_changes(project: Path) -> None:
    project = showcase_project(project)
    application = create_showcase_application(project, provider_factory=WorkbenchProvider)
    story_path = project / "origin/02-user-stories.yaml"
    before = story_path.read_text()
    proposed = before.replace(
        "authoritative meaning is unclear.",
        "authoritative meaning and the consequences of change are unclear.",
    ).replace("revision: 2", "revision: 3", 1)

    status, page = request(
        application,
        "/candidate",
        "POST",
        form={"layer_file": "02-user-stories.yaml", "proposed_text": proposed, "lang": "en"},
    )

    assert status == "200 OK"
    assert "Candidate impact" in page
    assert "story_authority_drift" in page
    assert "spec_candidate_impact_is_visible" in page
    assert story_path.read_text() == before


def test_workbench_can_open_each_origin_layer(project: Path) -> None:
    project = showcase_project(project)
    application = create_showcase_application(project, provider_factory=WorkbenchProvider)

    status, page = request(application, "/workbench", form={}, query="lang=en")
    assert status == "200 OK"
    assert "?layer=04-test-specifications.yaml" in page

    environ_path = "/workbench"
    payload = b""
    response: dict[str, str] = {}
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": environ_path,
        "QUERY_STRING": "layer=04-test-specifications.yaml",
        "CONTENT_LENGTH": "0",
        "wsgi.input": BytesIO(payload),
    }

    def start_response(status, headers):
        response["status"] = status

    body = b"".join(application(environ, start_response)).decode()
    assert response["status"] == "200 OK"
    assert 'value="04-test-specifications.yaml"' in body
    assert "spec_candidate_impact_is_visible" in body


def test_workbench_approval_applies_candidate_and_shows_history(project: Path) -> None:
    project = showcase_project(project)
    application = create_showcase_application(project, provider_factory=WorkbenchProvider)
    original = (project / "origin/02-user-stories.yaml").read_text()
    proposed = original.replace("revision: 2", "revision: 3", 1).replace(
        "authoritative meaning is unclear.", "approved consequences are unclear."
    )
    _, preview = request(
        application,
        "/candidate",
        "POST",
        form={"layer_file": "02-user-stories.yaml", "proposed_text": proposed, "lang": "en"},
    )
    candidate_id = preview.split('name="candidate_id" value="', 1)[1].split('"', 1)[0]

    status, page = request(
        application,
        "/candidate/approve",
        "POST",
        form={"candidate_id": candidate_id, "lang": "en"},
    )

    assert status == "200 OK"
    assert "Revision approved" in page
    assert "Change history" in page
    assert "approved consequences" in (project / "origin/02-user-stories.yaml").read_text()


def test_workbench_failed_approval_is_safe_and_does_not_expose_provider_detail(
    project: Path,
) -> None:
    project = showcase_project(project)
    application = create_showcase_application(project, provider_factory=FailingWorkbenchProvider)
    story_path = project / "origin/02-user-stories.yaml"
    original = story_path.read_text()
    proposed = original.replace("revision: 2", "revision: 3", 1).replace(
        "authoritative meaning is unclear.", "approval consequences are unclear."
    )
    _, preview = request(
        application,
        "/candidate",
        "POST",
        form={"layer_file": "02-user-stories.yaml", "proposed_text": proposed, "lang": "en"},
    )
    candidate_id = preview.split('name="candidate_id" value="', 1)[1].split('"', 1)[0]

    status, page = request(
        application,
        "/candidate/approve",
        "POST",
        form={"candidate_id": candidate_id, "lang": "en"},
    )

    assert status == "422 Unprocessable Entity"
    assert "Approval failed; the authoritative origin is unchanged." in page
    assert "sensitive provider detail" not in page
    assert story_path.read_text() == original
