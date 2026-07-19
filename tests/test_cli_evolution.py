from __future__ import annotations

from pathlib import Path
from shutil import copytree

import yaml

from dodai.cli import main
from dodai.projection import ProjectionContent, ProjectionEngine


class FixedProvider:
    def derive(self, origin_text: str) -> ProjectionContent:
        return ProjectionContent(
            product_name="CLI Product",
            audience="Product teams",
            headline="Govern change",
            value_proposition="Preview consequences.",
            call_to_action="Continue",
            stakeholder_summary="A traceable change.",
        )


def test_cli_previews_candidate_and_reports_impact(project: Path, tmp_path: Path, capsys) -> None:
    repository = Path(__file__).parents[1]
    copytree(repository / "pins", project / "pins")
    ProjectionEngine(project, FixedProvider()).project()
    layer = yaml.safe_load((project / "origin/02-user-stories.yaml").read_text())
    layer["revision"] += 1
    layer["stories"][0]["pain"] += " Consequences are unclear."
    candidate_path = tmp_path / "candidate.yaml"
    candidate_path.write_text(yaml.safe_dump(layer, sort_keys=False))

    code = main(
        [
            "--root",
            str(project),
            "preview",
            "02-user-stories.yaml",
            str(candidate_path),
        ]
    )

    output = capsys.readouterr().out
    assert code == 0
    assert "candidate " in output
    assert "story_authority_drift" in output
    assert "developer/waitlist.py" in output


def test_cli_derivability_rejects_an_unsupported_projection(project: Path, capsys) -> None:
    ProjectionEngine(project, FixedProvider()).project()
    brief = project / "projections/stakeholder/brief.md"
    brief.write_text(brief.read_text() + "\nUnsupported claim.\n")

    code = main(["--root", str(project), "derivability"])

    assert code == 1
    assert "stakeholder/brief.md" in capsys.readouterr().out
