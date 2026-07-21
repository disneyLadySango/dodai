from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dodai.delegation import (
    CodexCliRunner,
    DelegationExecutionError,
    DelegationResult,
    SampleDelegationRunner,
    collect_delegation_evidence,
    prepare_repository,
)


def test_repository_evidence_is_derived_from_git_changes(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    prepare_repository(repository, origin_summary="# Intent\n\nApproved outcome.")
    (repository / "implementation.txt").write_text("observable result\n")
    (repository / "product").mkdir()
    (repository / "product/index.html").write_text("<h1>Observable result</h1>\n")

    evidence = collect_delegation_evidence(
        repository,
        DelegationResult(
            summary="Implemented.",
            verification_status="passed",
            verification_summary="Verification passed.",
            stakeholder_summary="The outcome is available.",
        ),
        attempt=1,
    )

    assert [item["path"] for item in evidence.artifacts] == [
        "implementation.txt",
        "product/index.html",
    ]
    assert len(evidence.artifacts[0]["digest"]) == 64
    assert evidence.origin_evidence["story"] == "story_primary_pain"


def test_delegation_requires_an_experienceable_product(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    prepare_repository(repository, origin_summary="# Intent")
    (repository / "implementation.txt").write_text("not directly experienceable\n")

    with pytest.raises(ValueError, match="experienceable product"):
        collect_delegation_evidence(
            repository,
            DelegationResult("Done", "passed", "Passed", "Outcome"),
            attempt=1,
        )


def test_delegation_rejects_a_changed_artifact_that_may_contain_a_secret(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    prepare_repository(repository, origin_summary="# Intent")
    (repository / "unsafe.env").write_text("api_key=secret-value-that-must-not-escape\n")

    with pytest.raises(ValueError, match="may contain a secret"):
        collect_delegation_evidence(
            repository,
            DelegationResult("Done", "passed", "Passed", "Outcome"),
            attempt=1,
        )


def test_delegation_rejects_an_artifact_link_outside_the_repository(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    prepare_repository(repository, origin_summary="# Intent")
    private_file = tmp_path / "private.txt"
    private_file.write_text("private material\n")
    (repository / "outside.txt").symlink_to(private_file)

    with pytest.raises(ValueError, match="escapes the isolated repository"):
        collect_delegation_evidence(
            repository,
            DelegationResult("Done", "passed", "Passed", "Outcome"),
            attempt=1,
        )


def test_codex_cli_runner_uses_ephemeral_workspace_sandbox_and_structured_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    observed: dict[str, object] = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        result_path = Path(command[command.index("--output-last-message") + 1])
        result_path.write_text(
            json.dumps(
                {
                    "summary": "Implemented.",
                    "verification_status": "passed",
                    "verification_summary": "Verification passed.",
                    "stakeholder_summary": "Outcome available.",
                }
            )
        )
        output = json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "python -m unittest",
                    "exit_code": 0,
                },
            }
        )
        return subprocess.CompletedProcess(command, 0, output, "")

    monkeypatch.setattr("dodai.delegation.shutil.which", lambda _: "/usr/bin/codex")
    monkeypatch.setattr("dodai.delegation.subprocess.run", fake_run)

    result = CodexCliRunner().run(repository, "Implement the approved outcome.")
    command = observed["command"]

    assert result.verification_status == "passed"
    assert command[:2] == ["codex", "exec"]
    assert "--ephemeral" in command
    assert command[command.index("--sandbox") + 1] == "workspace-write"
    assert command[command.index("-C") + 1] == str(repository)
    assert "--output-schema" in command
    assert "--output-last-message" in command
    assert "--json" in command
    assert "--ignore-user-config" in command
    assert 'approval_policy="never"' in command
    assert 'shell_environment_policy.inherit="core"' in command
    assert "shell_environment_policy.ignore_default_excludes=false" in command
    assert observed["kwargs"]["capture_output"] is True
    assert result.verification_commands == ("python -m unittest",)


def test_codex_cli_failure_exposes_a_safe_actionable_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    monkeypatch.setattr("dodai.delegation.shutil.which", lambda _: "/usr/bin/codex")
    monkeypatch.setattr(
        "dodai.delegation.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, "", "401 Unauthorized sk-secret-that-must-not-be-shown"
        ),
    )

    with pytest.raises(DelegationExecutionError) as captured:
        CodexCliRunner().run(repository, "Implement.")

    assert captured.value.reason == "authentication"
    assert "Codex CLIの認証" in captured.value.public_message
    assert "sk-secret" not in captured.value.public_message


def test_codex_cli_recovers_handoff_from_artifacts_and_successful_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "product").mkdir()
    (repository / "product/index.html").write_text("<h1>Usable result</h1>\n")
    (repository / "STAKEHOLDER.md").write_text(
        "# Stakeholder handoff\n\nThe approved outcome is ready to inspect.\n"
    )
    output = json.dumps(
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": "node tests/verify.mjs",
                "exit_code": 0,
            },
        }
    )

    monkeypatch.setattr("dodai.delegation.shutil.which", lambda _: "/usr/bin/codex")
    monkeypatch.setattr(
        "dodai.delegation.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, output, ""),
    )

    result = CodexCliRunner().run(repository, "Implement.")

    assert result.verification_status == "passed"
    assert result.verification_commands == ("node tests/verify.mjs",)
    assert "The approved outcome is ready to inspect." in result.stakeholder_summary
    assert "成果と検証証拠" in result.summary


def test_sample_delegation_runs_verification_without_collecting_runtime_cache(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    prepare_repository(repository, origin_summary="# Intent")

    result = SampleDelegationRunner().run(repository, "ignored in inspectable sample mode")
    evidence = collect_delegation_evidence(repository, result, attempt=1)

    assert result.verification_status == "passed"
    assert {item["path"] for item in evidence.artifacts} == {
        "delivery.py",
        "product/index.html",
        "test_delivery.py",
        "STAKEHOLDER.md",
    }
    assert not any("__pycache__" in item["path"] for item in evidence.artifacts)
