from __future__ import annotations

from pathlib import Path
from shutil import copytree

import pytest
import yaml

from dodai.evolution import (
    approve_candidate,
    attribute_change,
    candidate_from_proposal,
    check_projection_derivability,
    prepare_candidate,
    reject_candidate,
)
from dodai.projection import ProjectionContent, ProjectionEngine


class FixedProvider:
    def derive(self, origin_text: str) -> ProjectionContent:
        return ProjectionContent(
            product_name="Evolving Product",
            audience="Product teams",
            headline="Change intent with confidence",
            value_proposition="See consequences before accepting a revision.",
            call_to_action="Continue",
            stakeholder_summary="A governed origin change remains traceable across roles.",
        )


class FailingProvider:
    def derive(self, origin_text: str) -> ProjectionContent:
        raise RuntimeError("Projection failed before approval.")


def complete_project(project: Path) -> Path:
    repository = Path(__file__).parents[1]
    copytree(repository / "pins", project / "pins")
    ProjectionEngine(project, FixedProvider()).project()
    return project


def revised_story_text(project: Path) -> str:
    path = project / "origin/02-user-stories.yaml"
    document = yaml.safe_load(path.read_text())
    document["revision"] += 1
    document["stories"][0]["pain"] += " The consequences remain hard to anticipate."
    return yaml.safe_dump(document, sort_keys=False)


def test_candidate_reports_downstream_impact_without_changing_origin(project: Path) -> None:
    complete_project(project)
    story_path = project / "origin/02-user-stories.yaml"
    before = story_path.read_bytes()

    candidate = prepare_candidate(project, "02-user-stories.yaml", revised_story_text(project))

    assert candidate.valid is True
    assert candidate.changed_records == ["story_authority_drift"]
    assert "ac_change_impact_visible" in candidate.affected_records
    assert "spec_candidate_impact_is_visible" in candidate.affected_records
    assert "developer/waitlist.py" in candidate.affected_projections
    assert story_path.read_bytes() == before


def test_rejection_leaves_origin_and_projections_unchanged(project: Path) -> None:
    complete_project(project)
    candidate = prepare_candidate(project, "02-user-stories.yaml", revised_story_text(project))
    before = {
        path.relative_to(project).as_posix(): path.read_bytes()
        for path in project.rglob("*")
        if path.is_file() and ".dodai/candidates" not in path.as_posix()
    }

    reject_candidate(project, candidate.candidate_id)

    after = {
        path.relative_to(project).as_posix(): path.read_bytes()
        for path in project.rglob("*")
        if path.is_file() and ".dodai/candidates" not in path.as_posix()
    }
    assert after == before


def test_approval_applies_complete_change_and_records_connected_history(project: Path) -> None:
    complete_project(project)
    candidate = prepare_candidate(project, "02-user-stories.yaml", revised_story_text(project))

    result = approve_candidate(
        project, candidate.candidate_id, FixedProvider(), approved_by="human"
    )

    stories = yaml.safe_load((project / "origin/02-user-stories.yaml").read_text())
    history = yaml.safe_load(result.history_path.read_text())
    assert "consequences remain hard" in stories["stories"][0]["pain"]
    assert history["approval"]["actor"] == "human"
    assert history["before"]["origin_digest"] != history["after"]["origin_digest"]
    assert history["validation"] == {"errors": [], "warnings": []}
    assert history["after"]["projection_digest"] == result.projection_digest


def test_failed_or_stale_approval_never_partially_changes_the_origin(project: Path) -> None:
    complete_project(project)
    candidate = prepare_candidate(project, "02-user-stories.yaml", revised_story_text(project))
    story_path = project / "origin/02-user-stories.yaml"
    before = story_path.read_bytes()

    with pytest.raises(RuntimeError, match="Projection failed"):
        approve_candidate(project, candidate.candidate_id, FailingProvider(), approved_by="human")
    assert story_path.read_bytes() == before

    story_path.write_text(story_path.read_text() + "\n")
    with pytest.raises(ValueError, match="changed after the candidate"):
        approve_candidate(project, candidate.candidate_id, FixedProvider(), approved_by="human")


def test_guardrail_proposal_becomes_a_layer_four_candidate(project: Path) -> None:
    proposal = project / "proposal.yaml"
    proposal.write_text(
        yaml.safe_dump(
            {
                "based_on": "guardrail_regeneration_budget",
                "proposed_test_specification": {
                    "id": "spec_observed_regeneration_bottleneck",
                    "verifies": ["guardrail_regeneration_budget"],
                    "given": "Observed reference conditions.",
                    "when": "A complete regeneration is observed.",
                    "then": "The exceeded outcome boundary is identified.",
                },
            }
        )
    )

    candidate = candidate_from_proposal(project, proposal)

    assert candidate.valid is True
    proposed = yaml.safe_load(candidate.proposed_text)
    assert proposed["specifications"][-1]["id"] == "spec_observed_regeneration_bottleneck"
    assert (project / "origin/04-test-specifications.yaml").read_text() != candidate.proposed_text


def test_losing_record_blocks_a_candidate_that_repeats_the_disproven_bet(project: Path) -> None:
    path = project / "origin/02-user-stories.yaml"
    document = yaml.safe_load(path.read_text())
    document["stories"][3]["losing_records"] = [
        {
            "id": "lost-one",
            "bet": "single unrestricted model output",
            "evidence": "It remained unstable across revisions.",
        }
    ]
    path.write_text(yaml.safe_dump(document, sort_keys=False))
    proposed_document = yaml.safe_load(revised_story_text(project))
    proposed_document["stories"][0]["pain"] += " Use a single unrestricted model output."
    proposed = yaml.safe_dump(proposed_document, sort_keys=False)

    candidate = prepare_candidate(project, "02-user-stories.yaml", proposed)

    assert candidate.valid is False
    assert candidate.blocked_by_losing_records == ["single unrestricted model output"]


def test_projection_change_is_attributed_or_rejected(project: Path) -> None:
    complete_project(project)
    baseline = attribute_change(project)
    assert baseline.cause == "none"

    pin = project / "pins/sample.yaml"
    pin.write_text(pin.read_text() + "presentation_tone: concise\n")
    assert attribute_change(project).cause == "pin"

    ProjectionEngine(project, FixedProvider()).project()
    projection = project / "projections/stakeholder/brief.md"
    projection.write_text(projection.read_text() + "\nUnsupported claim.\n")
    report = check_projection_derivability(project)
    assert report.valid is False
    assert report.unsupported == ["stakeholder/brief.md"]
