from __future__ import annotations

from pathlib import Path

import yaml

from dodai.origin import load_origin, validate_origin


def test_approved_origin_is_valid(project: Path) -> None:
    report = validate_origin(load_origin(project / "origin"))

    assert report.errors == []
    assert report.warnings == []


def test_solution_vocabulary_in_story_is_reported(project: Path) -> None:
    story_path = project / "origin" / "02-user-stories.yaml"
    document = yaml.safe_load(story_path.read_text())
    document["stories"][0]["pain"] += " They need a dashboard."
    story_path.write_text(yaml.safe_dump(document, sort_keys=False))

    report = validate_origin(load_origin(project / "origin"))

    assert report.errors == []
    assert len(report.warnings) == 1
    assert report.warnings[0].record_id == "story_authority_drift"
    assert report.warnings[0].term == "dashboard"


def test_each_criterion_is_covered_by_a_test_specification(project: Path) -> None:
    origin = load_origin(project / "origin")

    criterion_ids = {criterion["id"] for criterion in origin.criteria}
    covered_ids = {
        criterion_id
        for specification in origin.specifications
        for criterion_id in specification["verifies"]
    }

    assert covered_ids == criterion_ids
