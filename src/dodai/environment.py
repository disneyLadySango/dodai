from __future__ import annotations

import os
import subprocess
from pathlib import Path

SUPPORTED_KEYS = {"OPENAI_API_KEY", "CODEX_API_KEY"}


def load_local_environment(root: Path) -> None:
    candidates = [root / ".env"]
    shared_root = _shared_repository_root(root)
    if shared_root is not None and shared_root != root:
        candidates.append(shared_root / ".env")
    for candidate in candidates:
        if not candidate.is_file():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            if key not in SUPPORTED_KEYS or key in os.environ:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            if value:
                os.environ[key] = value
        return


def _shared_repository_root(root: Path) -> Path | None:
    completed = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    common = Path(completed.stdout.strip())
    if not common.is_absolute():
        common = root / common
    return common.resolve().parent
