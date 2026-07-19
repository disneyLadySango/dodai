from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dodai.origin import load_origin, validate_origin
from dodai.outer_loop import evaluate_telemetry
from dodai.projection import OpenAIContentProvider, ProjectionEngine, SampleContentProvider
from dodai.rebuild import rebuild_and_compare


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dodai", description="Project role-specific artifacts from one origin."
    )
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="Project root (default: current directory)."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("lint", help="Validate origin structure and vocabulary.")
    project = commands.add_parser("project", help="Regenerate every active projection.")
    project.add_argument(
        "--sample", action="store_true", help="Use the keyless inspectable sample provider."
    )
    project.add_argument(
        "--refresh",
        action="store_true",
        help="Derive new semantic content even when an approved cache exists.",
    )
    telemetry = commands.add_parser("telemetry", help="Evaluate simulated telemetry.")
    telemetry.add_argument("path", type=Path)
    commands.add_parser(
        "rebuild-test", help="Rebuild projections and report observable differences."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root: Path = args.root.resolve()
    if args.command == "lint":
        report = validate_origin(load_origin(root / "origin"))
        for error in report.errors:
            print(f"error: {error}")
        for warning in report.warnings:
            print(f"warning: layer {warning.layer} {warning.record_id}: {warning.message}")
        if report.errors:
            return 1
        print(f"Origin valid with {len(report.warnings)} warning(s).")
        return 0
    if args.command == "project":
        provider = SampleContentProvider() if args.sample else OpenAIContentProvider()
        projection_result = ProjectionEngine(root, provider).project(refresh=args.refresh)
        state = "changed" if projection_result.changed else "stable"
        print(
            f"Projected {len(projection_result.files)} files "
            f"({state}, origin {projection_result.digest[:12]})."
        )
        return 0
    if args.command == "telemetry":
        telemetry_result = evaluate_telemetry(root, args.path.resolve())
        print(f"{telemetry_result.action}: {telemetry_result.reason}")
        if telemetry_result.proposal_path:
            print(telemetry_result.proposal_path)
        return 0
    if args.command == "rebuild-test":
        rebuild_result = rebuild_and_compare(root)
        if rebuild_result.matches:
            print("Rebuild matches every current projection.")
            return 0
        print("Rebuild differences:")
        for path in rebuild_result.differences:
            print(f"- {path}")
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
