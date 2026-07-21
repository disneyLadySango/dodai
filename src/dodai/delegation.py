from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

import yaml


@dataclass(frozen=True)
class DelegationResult:
    summary: str
    verification_status: str
    verification_summary: str
    stakeholder_summary: str
    verification_commands: tuple[str, ...] = ()


@dataclass(frozen=True)
class DelegationEvidence:
    attempt: int
    status: str
    summary: str
    verification_status: str
    verification_summary: str
    verification_commands: tuple[str, ...]
    stakeholder_summary: str
    artifacts: list[dict[str, str]]
    origin_evidence: dict[str, str]


class DelegationRunner(Protocol):
    def run(self, repository: Path, prompt: str) -> DelegationResult: ...


RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "verification_status": {"type": "string", "enum": ["passed", "failed"]},
        "verification_summary": {"type": "string"},
        "stakeholder_summary": {"type": "string"},
    },
    "required": [
        "summary",
        "verification_status",
        "verification_summary",
        "stakeholder_summary",
    ],
    "additionalProperties": False,
}

SECRET_PATTERN = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{20,}|(?:api[_-]?key|token|password)\s*[:=]\s*[^\s$<{]+)",
    re.IGNORECASE,
)


class CodexCliRunner:
    """Runs one non-interactive Codex attempt inside an isolated repository."""

    def __init__(self, executable: str = "codex", timeout_seconds: int = 600) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def run(self, repository: Path, prompt: str) -> DelegationResult:
        if shutil.which(self.executable) is None:
            raise RuntimeError("Codex CLI is not available.")
        control = repository.parent
        schema_path = control / "result-schema.json"
        result_path = control / "result.json"
        schema_path.write_text(json.dumps(RESULT_SCHEMA, indent=2) + "\n", encoding="utf-8")
        result_path.unlink(missing_ok=True)
        command = [
            self.executable,
            "exec",
            "--ephemeral",
            "--sandbox",
            "workspace-write",
            "--color",
            "never",
            "--json",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(result_path),
            "-C",
            str(repository),
            prompt,
        ]
        completed = subprocess.run(
            command,
            cwd=repository,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0 or not result_path.exists():
            raise RuntimeError("Codex did not complete the delegated attempt.")
        value = json.loads(result_path.read_text(encoding="utf-8"))
        result = DelegationResult(**value)
        if result.verification_status not in {"passed", "failed"}:
            raise ValueError("Delegation verification status is invalid.")
        commands = _successful_commands(completed.stdout)
        if result.verification_status == "passed" and not commands:
            raise ValueError("Delegation reported success without executed verification.")
        return DelegationResult(
            summary=result.summary,
            verification_status=result.verification_status,
            verification_summary=result.verification_summary,
            stakeholder_summary=result.stakeholder_summary,
            verification_commands=commands,
        )


class SampleDelegationRunner:
    """Provides a keyless, inspectable delegation path for evaluation."""

    def run(self, repository: Path, prompt: str) -> DelegationResult:
        (repository / "delivery.py").write_text(
            '"""Inspectable delegated result for the approved sample intent."""\n\n'
            "def describe_delivery() -> str:\n"
            '    return "approved outcome available"\n',
            encoding="utf-8",
        )
        (repository / "test_delivery.py").write_text(
            "import unittest\n\n"
            "from delivery import describe_delivery\n\n\n"
            "class DeliveryTest(unittest.TestCase):\n"
            "    def test_approved_outcome_is_available(self) -> None:\n"
            '        self.assertEqual(describe_delivery(), "approved outcome available")\n',
            encoding="utf-8",
        )
        (repository / "STAKEHOLDER.md").write_text(
            "# Delegation result\n\n"
            "The approved outcome is represented by a runnable, verified sample.\n",
            encoding="utf-8",
        )
        verification = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-q"],
            cwd=repository,
            capture_output=True,
            text=True,
            check=False,
        )
        return DelegationResult(
            summary="承認済みの意図から、検証可能な委譲結果を1つ作成しました。",
            verification_status="passed" if verification.returncode == 0 else "failed",
            verification_summary=(
                "サンプル成果の検証に成功しました。"
                if verification.returncode == 0
                else "サンプル成果の検証に失敗しました。"
            ),
            stakeholder_summary="承認済みの成果を、関係者が確認できる状態にしました。",
            verification_commands=("python -m unittest discover -q",),
        )


def prepare_repository(repository: Path, *, origin_summary: str) -> None:
    repository.mkdir(parents=True, exist_ok=True)
    if (repository / ".git").exists():
        return
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Dodai")
    _git(repository, "config", "user.email", "dodai@localhost")
    (repository / "AGENTS.md").write_text(
        "# Delegated product work\n\n"
        "Work only inside this repository. Implement one usable vertical journey from ORIGIN.md. "
        "Choose technical methods independently. Add automated verification and STAKEHOLDER.md. "
        "Run the relevant verification before reporting completion. Never include credentials, "
        "tokens, personal data, or Codex session identifiers.\n",
        encoding="utf-8",
    )
    (repository / "ORIGIN.md").write_text(origin_summary.rstrip() + "\n", encoding="utf-8")
    (repository / "README.md").write_text(
        "# Delegated product repository\n\n"
        "This repository is managed as one isolated Dodai delegation.\n",
        encoding="utf-8",
    )
    (repository / ".gitignore").write_text(
        "__pycache__/\n*.py[cod]\n.pytest_cache/\n.venv/\nnode_modules/\n",
        encoding="utf-8",
    )
    _git(repository, "add", ".gitignore", "AGENTS.md", "ORIGIN.md", "README.md")
    _git(repository, "commit", "-m", "chore: initialize delegated product intent")


def collect_delegation_evidence(
    repository: Path,
    result: DelegationResult,
    *,
    attempt: int,
) -> DelegationEvidence:
    status = _git(repository, "status", "--porcelain", "--untracked-files=all")
    artifacts = []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        relative = line[3:].split(" -> ")[-1]
        path = repository / relative
        repository_root = repository.resolve()
        if path.is_symlink() or not path.resolve().is_relative_to(repository_root):
            raise ValueError(f"Delegated artifact escapes the isolated repository: {relative}")
        if (
            not path.is_file()
            or ".git" in path.parts
            or "__pycache__" in path.parts
            or path.suffix == ".pyc"
        ):
            continue
        content = path.read_bytes()
        if SECRET_PATTERN.search(content.decode("utf-8", errors="ignore")):
            raise ValueError(f"Delegated artifact may contain a secret: {relative}")
        artifacts.append(
            {
                "path": relative,
                "change": line[:2].strip() or "modified",
                "digest": sha256(content).hexdigest(),
            }
        )
    if not artifacts:
        raise ValueError("Delegation completed without changed artifacts.")
    return DelegationEvidence(
        attempt=attempt,
        status="completed",
        summary=result.summary,
        verification_status=result.verification_status,
        verification_summary=result.verification_summary,
        verification_commands=result.verification_commands,
        stakeholder_summary=result.stakeholder_summary,
        artifacts=sorted(artifacts, key=lambda item: item["path"]),
        origin_evidence={
            "story": "story_primary_pain",
            "criterion": "ac_primary_outcome",
            "specification": "spec_primary_outcome_is_observable",
        },
    )


def write_delegation_evidence(workspace: Path, evidence: DelegationEvidence) -> Path:
    destination = workspace / ".dodai" / "delegation" / "evidence.yaml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".yaml.tmp")
    temporary.write_text(
        yaml.safe_dump(asdict(evidence), sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    temporary.replace(destination)
    return destination


def load_delegation_evidence(workspace: Path) -> dict[str, Any]:
    value = yaml.safe_load(
        (workspace / ".dodai" / "delegation" / "evidence.yaml").read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise ValueError("Delegation evidence must be a mapping.")
    return value


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Repository operation failed: git {arguments[0]}")
    return completed.stdout


def _successful_commands(output: str) -> tuple[str, ...]:
    commands = []
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item", {})
        if (
            event.get("type") == "item.completed"
            and item.get("type") == "command_execution"
            and item.get("exit_code") == 0
            and isinstance(item.get("command"), str)
        ):
            commands.append(item["command"])
    return tuple(commands)
