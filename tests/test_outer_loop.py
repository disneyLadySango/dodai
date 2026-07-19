from __future__ import annotations

from pathlib import Path

import yaml

from dodai.outer_loop import evaluate_telemetry


def test_guardrail_breach_proposes_revised_spec_without_changing_story(project: Path) -> None:
    story_path = project / "origin/02-user-stories.yaml"
    before = story_path.read_bytes()
    telemetry = project / "telemetry.yaml"
    telemetry.write_text(
        yaml.safe_dump(
            {
                "bet": "sample-waitlist",
                "elapsed_time": 150,
                "variable_model_cost": 0.20,
                "rebuild_mismatch": False,
                "representation_revision": 1,
            }
        )
    )

    result = evaluate_telemetry(project, telemetry)

    assert result.action == "revise_test_specifications"
    assert result.proposal_path is not None and result.proposal_path.is_file()
    assert story_path.read_bytes() == before


def test_exit_condition_appends_one_idempotent_losing_record(project: Path) -> None:
    telemetry = project / "telemetry.yaml"
    telemetry.write_text(
        yaml.safe_dump(
            {
                "bet": "origin-representation-v1",
                "elapsed_time": 10,
                "variable_model_cost": 0.10,
                "rebuild_mismatch": True,
                "representation_revision": 3,
                "evidence": "Mismatch persisted across revisions 1, 2, and 3.",
            }
        )
    )

    first = evaluate_telemetry(project, telemetry)
    second = evaluate_telemetry(project, telemetry)
    stories = yaml.safe_load((project / "origin/02-user-stories.yaml").read_text())["stories"]
    failure_story = next(story for story in stories if story["id"] == "story_failure_diagnosis")

    assert first.action == "record_loss"
    assert second.action == "record_loss"
    assert len(failure_story["losing_records"]) == 1
    assert failure_story["losing_records"][0]["bet"] == "origin-representation-v1"
