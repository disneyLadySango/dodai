from __future__ import annotations

from pathlib import Path

import yaml

from dodai.origin import load_origin, validate_origin


def _write(path: Path, value: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")


def initialize_workspace(root: Path, *, name: str, who: str, pain: str, journey: str) -> None:
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"Workspace is not empty: {root}")
    origin = root / "origin"
    pins = root / "pins"
    origin.mkdir(parents=True, exist_ok=True)
    pins.mkdir(parents=True, exist_ok=True)
    _write(
        origin / "01-definitions.yaml",
        {
            "origin": name,
            "layer": {"number": 1, "name": "definitions"},
            "revision": 1,
            "terms": [
                {
                    "id": "origin",
                    "definition": "The sole authority for product intent and constraints.",
                    "allowed_layers": [1, 2, 3, 4],
                },
                {
                    "id": "projection",
                    "definition": "A role-specific presentation derived from the origin.",
                    "allowed_layers": [1, 2, 3, 4],
                },
            ],
            "boundary_terms": {
                "story_solution_vocabulary": {
                    "forbidden_in": [2],
                    "examples": ["API", "dashboard", "database", "framework", "server"],
                },
                "test_implementation_nouns": {
                    "forbidden_in": [4],
                    "examples": ["API", "database", "framework", "function", "table"],
                },
            },
        },
    )
    _write(
        origin / "02-user-stories.yaml",
        {
            "origin": name,
            "layer": {"number": 2, "name": "user_stories"},
            "revision": 1,
            "stories": [{"id": "story_primary_pain", "who": who, "pain": pain}],
        },
    )
    _write(
        origin / "03-acceptance-criteria.yaml",
        {
            "origin": name,
            "layer": {"number": 3, "name": "acceptance_criteria"},
            "revision": 1,
            "criteria": [
                {
                    "id": "ac_role_alignment",
                    "kind": "outcome",
                    "supports": ["story_primary_pain"],
                    "statement": (
                        "The same product meaning is available as executable verification and "
                        "a human-readable explanation."
                    ),
                }
            ],
        },
    )
    _write(
        origin / "04-test-specifications.yaml",
        {
            "origin": name,
            "layer": {"number": 4, "name": "test_specifications"},
            "revision": 1,
            "specifications": [
                {
                    "id": "spec_roles_share_meaning",
                    "verifies": ["ac_role_alignment"],
                    "given": "One valid origin describing a minimal product journey.",
                    "when": "The complete active projection set is requested.",
                    "then": (
                        "Executable verification and a human-readable explanation agree on "
                        "the product meaning."
                    ),
                }
            ],
        },
    )
    _write(
        pins / "projection.yaml",
        {"projection_kind": "brief", "journey": journey},
    )
    _write(
        pins / "presentation-map.yaml",
        {
            "presentations": [
                {
                    "path": path,
                    "role": role,
                    "story": "story_primary_pain",
                    "criterion": "ac_role_alignment",
                    "specification": "spec_roles_share_meaning",
                }
                for path, role in (
                    ("developer/experience.py", "developer"),
                    ("developer/test_experience.py", "developer"),
                    ("stakeholder/brief.md", "stakeholder"),
                )
            ]
        },
    )
    report = validate_origin(load_origin(origin))
    if not report.valid or report.warnings:
        raise ValueError("The initialized origin did not pass validation.")
