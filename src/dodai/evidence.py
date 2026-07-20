from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from dodai.origin import load_origin


@dataclass(frozen=True)
class FailureDiagnosis:
    layer: str
    finding: str
    retained: str
    next_change: str


FAILURE_DIAGNOSES = {
    "problem_not_observed": FailureDiagnosis(
        layer="第2層",
        finding="課題の見立てが証拠と一致していません。",
        retained="観測された事実と、まだ否定されていない成果条件",
        next_change="第2層の利用者と痛みの見立て",
    ),
    "behavior_passed_outcome_failed": FailureDiagnosis(
        layer="第4層",
        finding="生成された成果は検証を通過しましたが、期待した成果につながらず、確かめ方が不十分です。",
        retained="第2層の課題と第3層の成果条件",
        next_change="第4層の確かめ方",
    ),
    "behavior_failed": FailureDiagnosis(
        layer="Presentation",
        finding="生成された成果が承認済みの検証を満たしていません。",
        retained="原点4層の承認済み意図と検証",
        next_change="生成された成果",
    ),
    "insufficient_evidence": FailureDiagnosis(
        layer="判断不能",
        finding="現在の証拠だけでは、どの層が誤っているか判断できません。",
        retained="承認済みの原点と現在のPresentation",
        next_change="追加の証拠を集める観測",
    ),
}


def diagnose_failure(evidence_kind: str) -> FailureDiagnosis:
    return FAILURE_DIAGNOSES.get(evidence_kind, FAILURE_DIAGNOSES["insufficient_evidence"])


def write_presentation_evidence(root: Path, active_files: list[str]) -> Path:
    origin = load_origin(root / "origin")
    mapping_path = root / "pins" / "presentation-map.yaml"
    if mapping_path.exists():
        mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    else:
        story = origin.stories[0]["id"]
        criterion = origin.criteria[0]["id"]
        specification = next(
            item["id"] for item in origin.specifications if criterion in item.get("verifies", [])
        )
        mapping = {
            "presentations": [
                {
                    "path": path,
                    "role": "stakeholder" if path.startswith("stakeholder/") else "developer",
                    "story": story,
                    "criterion": criterion,
                    "specification": specification,
                }
                for path in active_files
            ]
        }
    if not isinstance(mapping, dict) or not isinstance(mapping.get("presentations"), list):
        raise ValueError("Presentation mapping must declare presentations.")

    story_ids = {item["id"] for item in origin.stories}
    criterion_ids = {item["id"] for item in origin.criteria}
    specification_ids = {item["id"] for item in origin.specifications}
    criteria = {item["id"]: item for item in origin.criteria}
    specifications = {item["id"]: item for item in origin.specifications}
    presentations: list[dict[str, Any]] = mapping["presentations"]
    mapped_paths = {str(item.get("path", "")) for item in presentations}
    if mapped_paths != set(active_files):
        missing = sorted(set(active_files) - mapped_paths)
        extra = sorted(mapped_paths - set(active_files))
        raise ValueError(f"Presentation mapping mismatch; missing={missing}, extra={extra}")
    for item in presentations:
        if item.get("story") not in story_ids:
            raise ValueError(f"Unknown story for presentation {item.get('path')}")
        if item.get("criterion") not in criterion_ids:
            raise ValueError(f"Unknown criterion for presentation {item.get('path')}")
        if item.get("specification") not in specification_ids:
            raise ValueError(f"Unknown specification for presentation {item.get('path')}")
        if item["story"] not in criteria[item["criterion"]].get("supports", []):
            raise ValueError(
                f"Criterion {item['criterion']} does not support story {item['story']}"
            )
        if item["criterion"] not in specifications[item["specification"]].get("verifies", []):
            raise ValueError(
                f"Specification {item['specification']} does not verify criterion "
                f"{item['criterion']}"
            )

    destination = root / "projections" / "evidence.yaml"
    destination.write_text(
        yaml.safe_dump(
            {"origin": origin.definitions["origin"], "presentations": presentations},
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return destination
