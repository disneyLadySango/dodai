from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from dodai.origin import load_origin


@dataclass(frozen=True)
class OuterLoopResult:
    action: str
    reason: str
    proposal_path: Path | None = None


def _read(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Telemetry must be a mapping.")
    return value


def evaluate_telemetry(root: Path, telemetry_path: Path) -> OuterLoopResult:
    telemetry = _read(telemetry_path)
    origin = load_origin(root / "origin")
    exit_criterion = next(item for item in origin.criteria if item["kind"] == "exit_condition")
    exit_threshold = int(exit_criterion["measure"]["threshold"])
    reached_exit = (
        telemetry.get("rebuild_mismatch")
        and int(telemetry.get("representation_revision", 0)) >= exit_threshold
    )
    if reached_exit:
        _append_losing_record(root, telemetry)
        return OuterLoopResult(
            action="record_loss",
            reason=f"Exit condition reached after {exit_threshold} representation revisions.",
        )

    guardrail = next(item for item in origin.criteria if item["kind"] == "guardrail")
    thresholds = {measure["name"]: measure["threshold"] for measure in guardrail["measures"]}
    breached = [
        name
        for name, threshold in thresholds.items()
        if float(telemetry.get(name, 0)) > float(threshold)
    ]
    if breached:
        proposal_path = _write_proposal(root, telemetry, breached)
        return OuterLoopResult(
            action="revise_test_specifications",
            reason=f"Guardrail breached: {', '.join(breached)}.",
            proposal_path=proposal_path,
        )
    return OuterLoopResult(action="continue", reason="No guardrail or exit condition was reached.")


def _write_proposal(root: Path, telemetry: dict[str, Any], breached: list[str]) -> Path:
    evidence_id = sha256(yaml.safe_dump(telemetry, sort_keys=True).encode()).hexdigest()[:12]
    path = root / ".dodai" / "proposals" / f"{evidence_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    proposal = {
        "based_on": "guardrail_regeneration_budget",
        "evidence": {name: telemetry[name] for name in breached},
        "proposed_test_specification": {
            "id": f"spec_regeneration_budget_{evidence_id}",
            "verifies": ["guardrail_regeneration_budget"],
            "given": "The sample product and the observed reference conditions.",
            "when": "One complete regeneration is observed with comparable work separated.",
            "then": (
                "The result identifies which part of regeneration exceeded the active threshold."
            ),
        },
    }
    path.write_text(yaml.safe_dump(proposal, sort_keys=False), encoding="utf-8")
    return path


def _append_losing_record(root: Path, telemetry: dict[str, Any]) -> None:
    path = root / "origin" / "02-user-stories.yaml"
    document = _read(path)
    story = next(item for item in document["stories"] if item["id"] == "story_failure_diagnosis")
    records = story.setdefault("losing_records", [])
    bet = str(telemetry["bet"])
    evidence = str(telemetry.get("evidence", "Exit telemetry reached the active threshold."))
    record_id = sha256(f"{bet}\n{evidence}".encode()).hexdigest()[:12]
    if any(record.get("id") == record_id for record in records):
        return
    records.append({"id": record_id, "bet": bet, "evidence": evidence})
    document["revision"] = int(document["revision"]) + 1
    path.write_text(yaml.safe_dump(document, sort_keys=False, allow_unicode=True), encoding="utf-8")
