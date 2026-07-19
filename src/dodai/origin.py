from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml


@dataclass(frozen=True)
class Origin:
    directory: Path
    definitions: dict[str, Any]
    stories_document: dict[str, Any]
    criteria_document: dict[str, Any]
    specifications_document: dict[str, Any]

    @property
    def stories(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self.stories_document["stories"])

    @property
    def criteria(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self.criteria_document["criteria"])

    @property
    def specifications(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self.specifications_document["specifications"])

    def source_text(self) -> str:
        parts = []
        for path in sorted(self.directory.glob("*.yaml")):
            parts.append(f"# {path.name}\n{path.read_text(encoding='utf-8')}")
        return "\n".join(parts)


@dataclass(frozen=True)
class VocabularyWarning:
    layer: int
    record_id: str
    term: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    errors: list[str]
    warnings: list[VocabularyWarning]

    @property
    def valid(self) -> bool:
        return not self.errors


def _read(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path} must contain a mapping")
    return document


def load_origin(directory: Path) -> Origin:
    return Origin(
        directory=directory,
        definitions=_read(directory / "01-definitions.yaml"),
        stories_document=_read(directory / "02-user-stories.yaml"),
        criteria_document=_read(directory / "03-acceptance-criteria.yaml"),
        specifications_document=_read(directory / "04-test-specifications.yaml"),
    )


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", text, re.I) is not None


def validate_origin(origin: Origin) -> ValidationReport:
    errors: list[str] = []
    warnings: list[VocabularyWarning] = []
    story_ids = {story["id"] for story in origin.stories}
    criterion_ids = {criterion["id"] for criterion in origin.criteria}
    specification_ids = {specification["id"] for specification in origin.specifications}

    if len(story_ids) != len(origin.stories):
        errors.append("Layer 2 contains duplicate story identifiers.")
    if len(criterion_ids) != len(origin.criteria):
        errors.append("Layer 3 contains duplicate criterion identifiers.")
    if len(specification_ids) != len(origin.specifications):
        errors.append("Layer 4 contains duplicate specification identifiers.")

    covered = {
        criterion_id
        for specification in origin.specifications
        for criterion_id in specification.get("verifies", [])
    }
    missing = sorted(criterion_ids - covered)
    unknown = sorted(covered - criterion_ids)
    if missing:
        errors.append(f"Layer 3 criteria without test specifications: {', '.join(missing)}")
    if unknown:
        errors.append(f"Layer 4 references unknown criteria: {', '.join(unknown)}")

    for criterion in origin.criteria:
        for reference in criterion.get("supports", []):
            if reference not in story_ids | criterion_ids:
                errors.append(f"{criterion['id']} supports unknown record {reference}.")

    boundaries = origin.definitions.get("boundary_terms", {})
    story_terms = boundaries.get("story_solution_vocabulary", {}).get("examples", [])
    test_terms = boundaries.get("test_implementation_nouns", {}).get("examples", [])
    for story in origin.stories:
        pain = str(story.get("pain", ""))
        for term in story_terms:
            if _contains_term(pain, str(term)):
                warnings.append(
                    VocabularyWarning(
                        layer=2,
                        record_id=story["id"],
                        term=str(term),
                        message=f"Solution vocabulary '{term}' appears in a user story.",
                    )
                )
    for specification in origin.specifications:
        observable_text = " ".join(
            str(specification.get(field, "")) for field in ("given", "when", "then")
        )
        for term in test_terms:
            if _contains_term(observable_text, str(term)):
                warnings.append(
                    VocabularyWarning(
                        layer=4,
                        record_id=specification["id"],
                        term=str(term),
                        message=f"Implementation noun '{term}' appears in a test specification.",
                    )
                )
    return ValidationReport(errors=errors, warnings=warnings)
