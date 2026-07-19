from __future__ import annotations

import json
import textwrap
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

import yaml
from openai import OpenAI

from dodai.origin import load_origin, validate_origin

RENDERER_VERSION = "1"
DEFAULT_MODEL = "gpt-5.6"


@dataclass(frozen=True)
class ProjectionContent:
    product_name: str
    audience: str
    headline: str
    value_proposition: str
    call_to_action: str
    stakeholder_summary: str


class ContentProvider(Protocol):
    def derive(self, origin_text: str) -> ProjectionContent: ...


@dataclass(frozen=True)
class ProjectionResult:
    digest: str
    changed: bool
    files: list[str]


class OpenAIContentProvider:
    def __init__(self, model: str = DEFAULT_MODEL, client: OpenAI | None = None) -> None:
        self.model = model
        self.client = client or OpenAI()

    def derive(self, origin_text: str) -> ProjectionContent:
        schema = {
            "type": "object",
            "properties": {
                field: {"type": "string"} for field in ProjectionContent.__dataclass_fields__
            },
            "required": list(ProjectionContent.__dataclass_fields__),
            "additionalProperties": False,
        }
        response = self.client.responses.create(
            model=self.model,
            reasoning={"effort": "medium"},
            instructions=(
                "Derive concise product content for the pinned minimal waitlist journey. "
                "Honor the origin vocabulary and outcomes. Do not introduce capabilities."
            ),
            input=origin_text,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "projection_content",
                    "strict": True,
                    "schema": schema,
                }
            },
        )
        values = json.loads(response.output_text)
        return ProjectionContent(**values)


class SampleContentProvider:
    """Provides an inspectable keyless path for tests and judge evaluation."""

    def derive(self, origin_text: str) -> ProjectionContent:
        return ProjectionContent(
            product_name="dodai Early Access",
            audience="Product managers and engineers delegating implementation to AI agents",
            headline="Keep product intent and delivery on the same foundation",
            value_proposition=(
                "Join the waitlist to explore origin-driven delivery without "
                "technical micromanagement."
            ),
            call_to_action="Join the waitlist",
            stakeholder_summary=(
                "This waitlist journey demonstrates that one origin can produce aligned executable "
                "behavior, verification, and stakeholder communication."
            ),
        )


class ProjectionEngine:
    def __init__(self, root: Path, provider: ContentProvider) -> None:
        self.root = root
        self.provider = provider

    def _source_and_digest(self) -> tuple[str, str]:
        origin = load_origin(self.root / "origin")
        report = validate_origin(origin)
        if report.errors or report.warnings:
            messages = report.errors + [warning.message for warning in report.warnings]
            raise ValueError("Origin validation failed: " + "; ".join(messages))
        pin_text = ""
        pin_directory = self.root / "pins"
        if pin_directory.exists():
            pin_text = "\n".join(
                path.read_text(encoding="utf-8") for path in sorted(pin_directory.glob("*.yaml"))
            )
        source = origin.source_text() + "\n# projection pins\n" + pin_text
        digest = sha256(f"{RENDERER_VERSION}\n{source}".encode()).hexdigest()
        return source, digest

    def project(self, *, refresh: bool = False) -> ProjectionResult:
        source, digest = self._source_and_digest()
        cache_path = self.root / ".dodai" / "cache" / f"{digest}.yaml"
        if cache_path.exists() and not refresh:
            content = ProjectionContent(**yaml.safe_load(cache_path.read_text(encoding="utf-8")))
        else:
            content = self.provider.derive(source)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                yaml.safe_dump(asdict(content), sort_keys=True, allow_unicode=True),
                encoding="utf-8",
            )

        rendered = _render(content, digest)
        projection_root = self.root / "projections"
        before = (
            {
                path.relative_to(projection_root).as_posix(): path.read_bytes()
                for path in projection_root.rglob("*")
                if path.is_file()
            }
            if projection_root.exists()
            else {}
        )
        for relative_path, body in rendered.items():
            destination = projection_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(body, encoding="utf-8")
        after = {path: body.encode() for path, body in rendered.items()}
        return ProjectionResult(digest=digest, changed=before != after, files=sorted(rendered))


def _render(content: ProjectionContent, digest: str) -> dict[str, str]:
    product_name = _python_assignment("PRODUCT_NAME", content.product_name)
    headline = _python_assignment("HEADLINE", content.headline)
    value_proposition = _python_assignment("VALUE_PROPOSITION", content.value_proposition)
    call_to_action = _python_assignment("CALL_TO_ACTION", content.call_to_action)
    app = f'''"""Generated waitlist projection. Regenerate instead of editing."""

from __future__ import annotations

import json
import re
from pathlib import Path

{product_name}
{headline}
{value_proposition}
{call_to_action}


def register(email: str, records_path: Path) -> bool:
    normalized = email.strip().lower()
    if re.fullmatch(r"[^@\\s]+@[^@\\s]+\\.[^@\\s]+", normalized) is None:
        raise ValueError("Enter a valid email address.")
    records = json.loads(records_path.read_text()) if records_path.exists() else []
    if normalized in records:
        return False
    records.append(normalized)
    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text(json.dumps(records, indent=2) + "\\n")
    return True
'''
    test = """from pathlib import Path

import pytest
from waitlist import register


def test_registration_survives_a_new_call(tmp_path: Path) -> None:
    records = tmp_path / "registrations.json"
    assert register("Person@example.com", records) is True
    assert register("person@example.com", records) is False


def test_invalid_email_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="valid email"):
        register("not-an-email", tmp_path / "registrations.json")
"""
    brief = f"""# {content.product_name}

## Audience

{content.audience}

## Promise

**{content.headline}**

{content.value_proposition}

## Journey

A visitor understands the promise, chooses **{content.call_to_action}**, and a
valid registration remains available to later visits. Repeated registration is
recognized without creating a duplicate.

## Why this projection exists

{content.stakeholder_summary}
"""
    manifest = yaml.safe_dump(
        {
            "origin_digest": digest,
            "renderer_version": RENDERER_VERSION,
            "files": [
                "developer/waitlist.py",
                "developer/test_waitlist.py",
                "stakeholder/brief.md",
            ],
        },
        sort_keys=False,
    )
    return {
        "developer/waitlist.py": app,
        "developer/test_waitlist.py": test,
        "stakeholder/brief.md": brief,
        "manifest.yaml": manifest,
    }


def _python_assignment(name: str, value: str) -> str:
    encoded = json.dumps(value, ensure_ascii=False)
    if len(name) + len(encoded) + 3 <= 100:
        return f"{name} = {encoded}"
    chunks = textwrap.wrap(
        value,
        width=72,
        break_long_words=False,
        break_on_hyphens=False,
        drop_whitespace=False,
        replace_whitespace=False,
    )
    expression = "\n    + ".join(json.dumps(chunk, ensure_ascii=False) for chunk in chunks)
    return f"{name} = (\n    {expression}\n)"
