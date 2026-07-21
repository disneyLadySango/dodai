from __future__ import annotations

import os
from pathlib import Path

from dodai.environment import load_local_environment


def test_local_environment_loads_supported_keys_without_overwriting(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=local-openai-key\n"
        "CODEX_API_KEY='local-codex-key'\n"
        "UNRELATED_SECRET=must-not-load\n"
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CODEX_API_KEY", "already-set")
    monkeypatch.delenv("UNRELATED_SECRET", raising=False)

    load_local_environment(tmp_path)

    assert os.environ["OPENAI_API_KEY"] == "local-openai-key"
    assert os.environ["CODEX_API_KEY"] == "already-set"
    assert "UNRELATED_SECRET" not in os.environ


def test_worktree_uses_shared_repository_environment(tmp_path: Path, monkeypatch) -> None:
    shared_root = tmp_path / "main"
    worktree = tmp_path / "worktree"
    shared_root.mkdir()
    worktree.mkdir()
    (shared_root / ".env").write_text("OPENAI_API_KEY=shared-key\n")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("dodai.environment._shared_repository_root", lambda _: shared_root)

    load_local_environment(worktree)

    assert os.environ["OPENAI_API_KEY"] == "shared-key"
