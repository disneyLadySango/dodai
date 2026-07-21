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


class DelegationExecutionError(RuntimeError):
    """A bounded delegation failure safe to explain without retaining raw output."""

    def __init__(self, reason: str, public_message: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.public_message = public_message


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
            "--ignore-user-config",
            "-c",
            'approval_policy="never"',
            "-c",
            'shell_environment_policy.inherit="core"',
            "-c",
            "shell_environment_policy.ignore_default_excludes=false",
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
        try:
            completed = subprocess.run(
                command,
                cwd=repository,
                env=os.environ.copy(),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise DelegationExecutionError(
                "timeout",
                "Codexの実行時間が上限に達しました。承認済み意図を保ったまま再開できます。",
            ) from error
        commands = _successful_commands(completed.stdout)
        if completed.returncode == 0 and not result_path.exists():
            stakeholder_path = repository / "STAKEHOLDER.md"
            delivery_path = repository / "product" / "index.html"
            if commands and stakeholder_path.is_file() and delivery_path.is_file():
                return DelegationResult(
                    summary="Codexが作成した成果と検証証拠から、Dodaiが委譲結果を復元しました。",
                    verification_status="passed",
                    verification_summary=f"成功した検証コマンドを{len(commands)}件確認しました。",
                    stakeholder_summary=stakeholder_path.read_text(encoding="utf-8")[:4000],
                    verification_commands=commands,
                )
        if completed.returncode != 0 or not result_path.exists():
            diagnostic = completed.stderr.lower()
            if any(
                term in diagnostic for term in ("401", "unauthorized", "authentication", "login")
            ):
                raise DelegationExecutionError(
                    "authentication",
                    "Codex CLIの認証を確認してから、同じ意図で再開してください。",
                )
            if any(term in diagnostic for term in ("429", "rate limit", "quota")):
                raise DelegationExecutionError(
                    "capacity",
                    "Codexの利用上限により開始できませんでした。時間を置いて同じ意図で再開してください。",
                )
            raise DelegationExecutionError(
                "incomplete",
                "Codexが完了結果を返しませんでした。承認済み意図を保ったまま再開できます。",
            )
        try:
            value = json.loads(result_path.read_text(encoding="utf-8"))
            result = DelegationResult(**value)
        except (json.JSONDecodeError, TypeError) as error:
            raise DelegationExecutionError(
                "invalid_result",
                "Codexの完了結果を検証できませんでした。成果は採用せず、同じ意図で再開できます。",
            ) from error
        if result.verification_status not in {"passed", "failed"}:
            raise ValueError("Delegation verification status is invalid.")
        if result.verification_status == "passed" and not commands:
            raise DelegationExecutionError(
                "missing_verification",
                "成功した検証を確認できないため、成果を採用候補にしませんでした。",
            )
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
        product = repository / "product"
        product.mkdir(exist_ok=True)
        (product / "index.html").write_text(
            """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>まちの夕市</title>
<style>
:root{--ink:#16231d;--paper:#fffaf0;--lime:#c9ff5b;--muted:#66736c}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:system-ui,sans-serif}
main{width:min(760px,calc(100% - 36px));margin:auto;padding:clamp(42px,10vw,90px) 0}
.eyebrow{font-size:.78rem;font-weight:900;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
h1{font-size:clamp(3rem,10vw,6.2rem);line-height:.9;letter-spacing:-.07em;margin:18px 0 24px}
.lede{font-size:1.15rem;line-height:1.7;max-width:560px;color:var(--muted)}
form,.result{border:1px solid var(--ink);padding:24px;margin-top:36px;background:white}
label{display:block;font-weight:850;margin-bottom:8px}
input{width:100%;padding:14px;border:1px solid #aab1ad;font:inherit}
button{margin-top:16px;border:0;background:var(--lime);color:var(--ink);padding:15px 20px}
button{font:inherit;font-weight:900;cursor:pointer}
.result{display:none;background:#eaffc7}
.result strong{display:block;font-size:1.4rem;margin-bottom:8px}
</style>
</head>
<body><main><p class="eyebrow">地域イベント参加受付</p><h1>まちの夕市</h1>
<p class="lede">参加意思を主催者へ伝え、その場で受付済みだと確認できます。</p>
<form id="join"><label for="name">お名前</label>
<input id="name" required placeholder="例: 山田 花子">
<button>参加を申し込む →</button></form>
<section class="result" id="result" aria-live="polite">
<strong>受付が完了しました</strong><span id="message"></span></section>
</main><script>
document.querySelector('#join').addEventListener('submit',event=>{
  event.preventDefault();
  const name=document.querySelector('#name').value;
  document.querySelector('#join').style.display='none';
  document.querySelector('#message').textContent=`${name}さんの参加意思を主催者へ届けました。`;
  document.querySelector('#result').style.display='block';
});
</script></body></html>
""",
            encoding="utf-8",
        )
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
        "Place an immediately usable static web result at product/index.html. "
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
    delivery = repository / "product" / "index.html"
    if (
        delivery.is_symlink()
        or not delivery.is_file()
        or not delivery.resolve().is_relative_to(repository.resolve())
    ):
        raise ValueError("Delegation completed without an experienceable product.")
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
    rendered = yaml.safe_dump(asdict(evidence), sort_keys=False, allow_unicode=True)
    archive = destination.parent / "attempts" / f"{evidence.attempt}.yaml"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists() and archive.read_text(encoding="utf-8") != rendered:
        raise ValueError("Delegation attempt evidence cannot be overwritten.")
    if not archive.exists():
        archive_temporary = archive.with_suffix(".yaml.tmp")
        archive_temporary.write_text(rendered, encoding="utf-8")
        archive_temporary.replace(archive)
    temporary = destination.with_suffix(".yaml.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(destination)
    return destination


def load_delegation_evidence(workspace: Path) -> dict[str, Any]:
    value = yaml.safe_load(
        (workspace / ".dodai" / "delegation" / "evidence.yaml").read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise ValueError("Delegation evidence must be a mapping.")
    return value


def load_delegation_attempts(workspace: Path) -> list[dict[str, Any]]:
    directory = workspace / ".dodai" / "delegation" / "attempts"
    if not directory.exists():
        return []
    attempts = []
    for path in directory.glob("*.yaml"):
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Delegation attempt evidence must be a mapping.")
        attempts.append(value)
    return sorted(attempts, key=lambda item: int(item["attempt"]))


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
