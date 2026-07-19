from __future__ import annotations

from pathlib import Path
from shutil import copytree

import pytest


@pytest.fixture
def project(tmp_path: Path) -> Path:
    repository_root = Path(__file__).parents[1]
    copytree(repository_root / "origin", tmp_path / "origin")
    return tmp_path
