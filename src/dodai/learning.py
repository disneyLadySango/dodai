from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from dodai.evidence import diagnose_failure
from dodai.evolution import CandidateRevision, prepare_candidate
from dodai.product import solution_terms


@dataclass(frozen=True)
class InteractionDiagnosis:
    evidence_kind: str
    layer: str
    finding: str
    retained: str
    next_change: str


def origin_snapshot_digest(workspace: Path) -> str:
    origin = workspace / "origin"
    content = b"".join(
        path.name.encode() + b"\0" + path.read_bytes() + b"\0"
        for path in sorted(origin.glob("*.yaml"))
    )
    return sha256(content).hexdigest()


def diagnose_interaction(
    pain_present: str, behavior_worked: str, outcome_achieved: str
) -> InteractionDiagnosis:
    answers = {pain_present, behavior_worked, outcome_achieved}
    if not answers <= {"yes", "no", "unsure"}:
        raise ValueError("Interaction answers must be yes, no, or unsure.")
    if "unsure" in answers:
        kind = "insufficient_evidence"
    elif pain_present == "no":
        kind = "problem_not_observed"
    elif behavior_worked == "no":
        kind = "behavior_failed"
    elif outcome_achieved == "no":
        kind = "behavior_passed_outcome_failed"
    else:
        return InteractionDiagnosis(
            evidence_kind="outcome_achieved",
            layer="成立",
            finding="困りごとに対して、承認した成果が実際の操作で確認できました。",
            retained="承認済みの原点と現在のPresentation",
            next_change="現在の成果を採用する判断",
        )
    diagnosed = diagnose_failure(kind)
    return InteractionDiagnosis(
        kind,
        diagnosed.layer,
        diagnosed.finding,
        diagnosed.retained,
        diagnosed.next_change,
    )


def _write_once(path: Path, value: dict[str, Any]) -> Path:
    rendered = yaml.safe_dump(value, sort_keys=False, allow_unicode=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise ValueError("Recorded interaction evidence cannot be overwritten.")
        return path
    temporary = path.with_suffix(".yaml.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(path)
    return path


def record_interaction_evidence(
    workspace: Path,
    *,
    attempt: int,
    pain_present: str,
    behavior_worked: str,
    outcome_achieved: str,
    observation: str,
) -> Path:
    observation = observation.strip()
    if attempt < 1 or not observation:
        raise ValueError("A delegation attempt and observed fact are required.")
    diagnosis = diagnose_interaction(pain_present, behavior_worked, outcome_achieved)
    value: dict[str, Any] = {
        "attempt": attempt,
        "answers": {
            "pain_present": pain_present,
            "behavior_worked": behavior_worked,
            "outcome_achieved": outcome_achieved,
        },
        "observation": observation,
        "diagnosis": {
            "evidence_kind": diagnosis.evidence_kind,
            "failure_layer": diagnosis.layer,
            "finding": diagnosis.finding,
            "retained": diagnosis.retained,
            "next_change": diagnosis.next_change,
        },
    }
    evidence_id = sha256(yaml.safe_dump(value, sort_keys=True).encode()).hexdigest()[:16]
    value["evidence_id"] = evidence_id
    return _write_once(workspace / ".dodai/interactions" / f"{evidence_id}.yaml", value)


def load_interaction_evidence(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Interaction evidence must be a mapping.")
    return value


def prepare_reverification_candidate(workspace: Path, evidence_path: Path) -> CandidateRevision:
    evidence = load_interaction_evidence(evidence_path)
    if evidence.get("diagnosis", {}).get("evidence_kind") != "behavior_passed_outcome_failed":
        raise ValueError("Only an observed outcome gap can revise verification.")
    layer_path = workspace / "origin/04-test-specifications.yaml"
    layer = yaml.safe_load(layer_path.read_text(encoding="utf-8"))
    layer["revision"] = int(layer["revision"]) + 1
    target = next(
        item
        for item in layer["specifications"]
        if item["id"] == "spec_primary_outcome_is_observable"
    )
    target["then"] = (
        "The observed result demonstrates the declared outcome in actual use and resolves "
        "the previously recorded outcome gap."
    )
    return prepare_candidate(
        workspace,
        "04-test-specifications.yaml",
        yaml.safe_dump(layer, sort_keys=False, allow_unicode=True),
    )


def prepare_story_rediscovery_candidate(
    workspace: Path,
    evidence_path: Path,
    *,
    actor: str,
    pain: str,
) -> CandidateRevision:
    evidence = load_interaction_evidence(evidence_path)
    if evidence.get("diagnosis", {}).get("evidence_kind") != "problem_not_observed":
        raise ValueError("Only unobserved-problem evidence can open Story rediscovery.")
    actor = actor.strip()
    pain = pain.strip()
    if not actor or not pain:
        raise ValueError("A newly observed person and pain are required.")
    if solution_terms(pain):
        raise ValueError("The rediscovered pain contains solution language.")
    layer_path = workspace / "origin/02-user-stories.yaml"
    layer = yaml.safe_load(layer_path.read_text(encoding="utf-8"))
    layer["revision"] = int(layer["revision"]) + 1
    story = layer["stories"][0]
    disproven = f"{story['who']}: {story['pain']}"
    observation = str(evidence["observation"])
    loss_id = sha256(f"{disproven}\n{observation}".encode()).hexdigest()[:16]
    losses = story.setdefault("losing_records", [])
    if not any(item.get("id") == loss_id for item in losses):
        losses.append(
            {
                "id": loss_id,
                "bet": disproven,
                "evidence": observation,
            }
        )
    story["who"] = actor
    story["pain"] = pain
    return prepare_candidate(
        workspace,
        "02-user-stories.yaml",
        yaml.safe_dump(layer, sort_keys=False, allow_unicode=True),
    )
