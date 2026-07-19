from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

import yaml

from dodai.origin import Origin, load_origin, validate_origin
from dodai.projection import ContentProvider, ProjectionEngine
from dodai.rebuild import rebuild_and_compare

LAYER_COLLECTIONS = {
    "01-definitions.yaml": "terms",
    "02-user-stories.yaml": "stories",
    "03-acceptance-criteria.yaml": "criteria",
    "04-test-specifications.yaml": "specifications",
}


@dataclass(frozen=True)
class CandidateRevision:
    candidate_id: str
    layer_file: str
    proposed_text: str
    valid: bool
    errors: list[str]
    warnings: list[str]
    changed_records: list[str]
    affected_records: list[str]
    affected_projections: list[str]
    blocked_by_losing_records: list[str]


@dataclass(frozen=True)
class ApprovalResult:
    history_path: Path
    projection_digest: str


@dataclass(frozen=True)
class ChangeAttribution:
    cause: str


@dataclass(frozen=True)
class DerivabilityReport:
    valid: bool
    unsupported: list[str]


def _read_mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping.")
    return value


def _origin_digest(origin: Origin) -> str:
    return sha256(origin.source_text().encode()).hexdigest()


def _pin_text(root: Path) -> str:
    directory = root / "pins"
    if not directory.exists():
        return ""
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(directory.glob("*.yaml")))


def _pin_digest(root: Path) -> str:
    return sha256(_pin_text(root).encode()).hexdigest()


def _record_map(document: dict[str, Any], collection: str) -> dict[str, dict[str, Any]]:
    return {str(record["id"]): record for record in document.get(collection, [])}


def _changed_records(
    current: dict[str, Any], proposed: dict[str, Any], collection: str
) -> list[str]:
    before = _record_map(current, collection)
    after = _record_map(proposed, collection)
    return sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))


def _affected_records(origin: Origin, layer_file: str, changed: list[str]) -> list[str]:
    affected = set(changed)
    if layer_file == "01-definitions.yaml":
        affected.update(str(record["id"]) for record in origin.stories)
        affected.update(str(record["id"]) for record in origin.criteria)
        affected.update(str(record["id"]) for record in origin.specifications)
    if layer_file in {"01-definitions.yaml", "02-user-stories.yaml"}:
        criteria = {
            str(criterion["id"])
            for criterion in origin.criteria
            if set(map(str, criterion.get("supports", []))) & affected
        }
        affected.update(criteria)
    if layer_file != "04-test-specifications.yaml":
        specifications = {
            str(specification["id"])
            for specification in origin.specifications
            if set(map(str, specification.get("verifies", []))) & affected
        }
        affected.update(specifications)
    return sorted(affected)


def _semantic_strings(value: Any, *, key: str = "") -> list[str]:
    if key == "losing_records":
        return []
    if isinstance(value, dict):
        return [
            item
            for child_key, child in value.items()
            for item in _semantic_strings(child, key=str(child_key))
        ]
    if isinstance(value, list):
        return [item for child in value for item in _semantic_strings(child, key=key)]
    return [str(value)]


def _blocked_bets(origin: Origin, proposed: dict[str, Any]) -> list[str]:
    bets = [
        str(record["bet"])
        for story in origin.stories
        for record in story.get("losing_records", [])
        if record.get("bet")
    ]
    candidate_meaning = " ".join(_semantic_strings(proposed)).casefold()
    return sorted(bet for bet in bets if bet.casefold() in candidate_meaning)


def _candidate_path(root: Path, candidate_id: str) -> Path:
    return root / ".dodai/candidates" / f"{candidate_id}.yaml"


def _load_candidate(root: Path, candidate_id: str) -> CandidateRevision:
    value = _read_mapping(_candidate_path(root, candidate_id))
    return CandidateRevision(**value)


def prepare_candidate(root: Path, layer_file: str, proposed_text: str) -> CandidateRevision:
    if layer_file not in LAYER_COLLECTIONS:
        raise ValueError(f"Unsupported origin layer: {layer_file}")
    current_origin = load_origin(root / "origin")
    current_document = _read_mapping(root / "origin" / layer_file)
    proposed = yaml.safe_load(proposed_text)
    if not isinstance(proposed, dict):
        raise ValueError("A candidate layer must contain a mapping.")
    canonical_text = yaml.safe_dump(proposed, sort_keys=False, allow_unicode=True)
    with TemporaryDirectory(prefix="dodai-candidate-") as directory:
        candidate_origin = Path(directory) / "origin"
        shutil.copytree(root / "origin", candidate_origin)
        (candidate_origin / layer_file).write_text(canonical_text, encoding="utf-8")
        proposed_origin = load_origin(candidate_origin)
        validation = validate_origin(proposed_origin)
    changed = _changed_records(current_document, proposed, LAYER_COLLECTIONS[layer_file])
    affected = _affected_records(proposed_origin, layer_file, changed)
    blocked = _blocked_bets(current_origin, proposed)
    errors = list(validation.errors)
    warnings = [warning.message for warning in validation.warnings]
    candidate_id = sha256(
        f"{_origin_digest(current_origin)}\n{layer_file}\n{canonical_text}".encode()
    ).hexdigest()[:16]
    manifest_path = root / "projections/manifest.yaml"
    projections = []
    if changed and manifest_path.exists():
        projections = [str(path) for path in _read_mapping(manifest_path).get("files", [])]
    candidate = CandidateRevision(
        candidate_id=candidate_id,
        layer_file=layer_file,
        proposed_text=canonical_text,
        valid=not errors and not warnings and not blocked,
        errors=errors,
        warnings=warnings,
        changed_records=changed,
        affected_records=affected,
        affected_projections=sorted(projections),
        blocked_by_losing_records=blocked,
    )
    path = _candidate_path(root, candidate_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(candidate.__dict__, sort_keys=False), encoding="utf-8")
    return candidate


def reject_candidate(root: Path, candidate_id: str) -> None:
    _candidate_path(root, candidate_id).unlink(missing_ok=True)


def approve_candidate(
    root: Path, candidate_id: str, provider: ContentProvider, *, approved_by: str
) -> ApprovalResult:
    candidate = _load_candidate(root, candidate_id)
    if not candidate.valid:
        raise ValueError("Only a valid, unblocked candidate can be approved.")
    before_origin = load_origin(root / "origin")
    before_origin_digest = _origin_digest(before_origin)
    before_projection_digest = _read_mapping(root / "projections/manifest.yaml").get(
        "origin_digest"
    )
    with TemporaryDirectory(prefix="dodai-approval-") as directory:
        staged = Path(directory)
        shutil.copytree(root / "origin", staged / "origin")
        (staged / "origin" / candidate.layer_file).write_text(
            candidate.proposed_text, encoding="utf-8"
        )
        if (root / "pins").exists():
            shutil.copytree(root / "pins", staged / "pins")
        if (root / ".dodai/cache").exists():
            shutil.copytree(root / ".dodai/cache", staged / ".dodai/cache")
        projection = ProjectionEngine(staged, provider).project()
        validation = validate_origin(load_origin(staged / "origin"))
        if not validation.valid or validation.warnings:
            raise ValueError("The staged origin did not pass validation.")

        destination = root / "origin" / candidate.layer_file
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(candidate.proposed_text, encoding="utf-8")
        temporary.replace(destination)
        if (root / "projections").exists():
            shutil.rmtree(root / "projections")
        shutil.copytree(staged / "projections", root / "projections")
        staged_cache = staged / ".dodai/cache" / f"{projection.digest}.yaml"
        destination_cache = root / ".dodai/cache" / staged_cache.name
        destination_cache.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged_cache, destination_cache)

    history = {
        "candidate_id": candidate_id,
        "layer_file": candidate.layer_file,
        "approval": {
            "actor": approved_by,
            "recorded_at": datetime.now(UTC).isoformat(),
        },
        "before": {
            "origin_digest": before_origin_digest,
            "projection_digest": before_projection_digest,
        },
        "after": {
            "origin_digest": _origin_digest(load_origin(root / "origin")),
            "projection_digest": projection.digest,
        },
        "validation": {"errors": [], "warnings": []},
    }
    history_path = root / ".dodai/history" / f"{candidate_id}.yaml"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(yaml.safe_dump(history, sort_keys=False), encoding="utf-8")
    reject_candidate(root, candidate_id)
    return ApprovalResult(history_path=history_path, projection_digest=projection.digest)


def candidate_from_proposal(root: Path, proposal_path: Path) -> CandidateRevision:
    proposal = _read_mapping(proposal_path)
    proposed = cast(dict[str, Any], proposal["proposed_test_specification"])
    layer_path = root / "origin/04-test-specifications.yaml"
    layer = _read_mapping(layer_path)
    layer["revision"] = int(layer["revision"]) + 1
    specifications = cast(list[dict[str, Any]], layer["specifications"])
    if not any(item["id"] == proposed["id"] for item in specifications):
        specifications.append(proposed)
    return prepare_candidate(
        root,
        "04-test-specifications.yaml",
        yaml.safe_dump(layer, sort_keys=False, allow_unicode=True),
    )


def attribute_change(root: Path) -> ChangeAttribution:
    manifest = _read_mapping(root / "projections/manifest.yaml")
    current_origin = _origin_digest(load_origin(root / "origin"))
    if manifest.get("origin_source_digest") != current_origin:
        return ChangeAttribution(cause="origin")
    if manifest.get("pin_digest") != _pin_digest(root):
        return ChangeAttribution(cause="pin")
    return ChangeAttribution(cause="none")


def check_projection_derivability(root: Path) -> DerivabilityReport:
    result = rebuild_and_compare(root)
    return DerivabilityReport(valid=result.matches, unsupported=result.differences)
