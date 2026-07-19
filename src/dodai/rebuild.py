from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory

from dodai.projection import ProjectionContent, ProjectionEngine


@dataclass(frozen=True)
class RebuildResult:
    matches: bool
    differences: list[str]


class _CacheOnlyProvider:
    def derive(self, origin_text: str) -> ProjectionContent:
        raise RuntimeError("The approved projection cache is missing for this origin.")


def _snapshot(directory: Path) -> dict[str, bytes]:
    if not directory.exists():
        return {}
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


def rebuild_and_compare(root: Path) -> RebuildResult:
    before = _snapshot(root / "projections")
    with TemporaryDirectory(prefix="dodai-rebuild-") as temporary:
        rebuilt_root = Path(temporary)
        copytree(root / "origin", rebuilt_root / "origin")
        if (root / "pins").exists():
            copytree(root / "pins", rebuilt_root / "pins")
        if (root / ".dodai" / "cache").exists():
            copytree(root / ".dodai" / "cache", rebuilt_root / ".dodai" / "cache")
        ProjectionEngine(rebuilt_root, _CacheOnlyProvider()).project()
        after = _snapshot(rebuilt_root / "projections")
    differences = sorted(
        path for path in set(before) | set(after) if before.get(path) != after.get(path)
    )
    return RebuildResult(matches=not differences, differences=differences)
