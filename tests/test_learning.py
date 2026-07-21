from pathlib import Path

import pytest
import yaml

from dodai.learning import (
    diagnose_interaction,
    origin_snapshot_digest,
    prepare_reverification_candidate,
    record_interaction_evidence,
)
from dodai.product import ProductStore, approve_verification, record_outcomes, record_problem


@pytest.mark.parametrize(
    ("pain", "behavior", "outcome", "kind", "layer"),
    [
        ("no", "yes", "yes", "problem_not_observed", "第2層"),
        ("yes", "no", "no", "behavior_failed", "Presentation"),
        ("yes", "yes", "no", "behavior_passed_outcome_failed", "第4層"),
        ("yes", "yes", "yes", "outcome_achieved", "成立"),
        ("unsure", "yes", "no", "insufficient_evidence", "判断不能"),
    ],
)
def test_plain_answers_identify_the_next_learning_boundary(
    pain: str, behavior: str, outcome: str, kind: str, layer: str
) -> None:
    diagnosis = diagnose_interaction(pain, behavior, outcome)

    assert diagnosis.evidence_kind == kind
    assert diagnosis.layer == layer


def test_interaction_evidence_is_immutable_and_linked_to_an_attempt(tmp_path: Path) -> None:
    first = record_interaction_evidence(
        tmp_path,
        attempt=1,
        pain_present="yes",
        behavior_worked="yes",
        outcome_achieved="no",
        observation="申し込みは完了したが、主催者に届いたか分からなかった。",
    )
    second = record_interaction_evidence(
        tmp_path,
        attempt=1,
        pain_present="yes",
        behavior_worked="yes",
        outcome_achieved="no",
        observation="申し込みは完了したが、主催者に届いたか分からなかった。",
    )

    assert first == second
    value = yaml.safe_load(first.read_text())
    assert value["attempt"] == 1
    assert value["diagnosis"]["failure_layer"] == "第4層"
    assert value["observation"].startswith("申し込みは完了")


def test_origin_snapshot_changes_when_any_approved_layer_changes(tmp_path: Path) -> None:
    origin = tmp_path / "origin"
    origin.mkdir()
    for number in range(1, 5):
        (origin / f"0{number}-layer.yaml").write_text(f"revision: {number}\n")
    before = origin_snapshot_digest(tmp_path)

    (origin / "04-layer.yaml").write_text("revision: changed\n")

    assert origin_snapshot_digest(tmp_path) != before


def test_outcome_gap_prepares_only_a_layer_four_revision(tmp_path: Path) -> None:
    store = ProductStore(tmp_path)
    bet = store.create("Learning product")
    record_problem(store, bet.project_id, actor="PM", pain="成果を判断できない")
    record_outcomes(
        store,
        bet.project_id,
        outcome="成果を意図に照らして判断できる",
        journey="成果を触る → 結果を記録する",
    )
    approve_verification(store, bet.project_id)
    workspace = store.workspace(bet.project_id)
    story_before = (workspace / "origin/02-user-stories.yaml").read_bytes()
    criteria_before = (workspace / "origin/03-acceptance-criteria.yaml").read_bytes()

    evidence_path = record_interaction_evidence(
        workspace,
        attempt=1,
        pain_present="yes",
        behavior_worked="yes",
        outcome_achieved="no",
        observation="操作は完了したが、判断材料が不足した。",
    )
    candidate = prepare_reverification_candidate(workspace, evidence_path)

    assert candidate.layer_file == "04-test-specifications.yaml"
    assert (workspace / "origin/02-user-stories.yaml").read_bytes() == story_before
    assert (workspace / "origin/03-acceptance-criteria.yaml").read_bytes() == criteria_before
    assert candidate.affected_records == ["spec_primary_outcome_is_observable"]
