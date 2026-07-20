from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dodai.evolution import (
    approve_candidate,
    attribute_change,
    candidate_from_proposal,
    check_projection_derivability,
    prepare_candidate,
    reject_candidate,
)
from dodai.origin import load_origin, validate_origin
from dodai.outer_loop import evaluate_telemetry
from dodai.projection import OpenAIContentProvider, ProjectionEngine, SampleContentProvider
from dodai.rebuild import rebuild_and_compare
from dodai.showcase import serve_showcase
from dodai.workspace import initialize_workspace


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
    showcase = commands.add_parser("showcase", help="Run the judge-facing browser showcase.")
    showcase.add_argument("--host", default="127.0.0.1")
    showcase.add_argument("--port", type=int, default=8000)
    preview = commands.add_parser("preview", help="Preview a candidate origin revision.")
    preview.add_argument("layer_file")
    preview.add_argument("candidate_path", type=Path)
    approve = commands.add_parser("approve", help="Approve a valid candidate and regenerate.")
    approve.add_argument("candidate_id")
    approve.add_argument("--approved-by", default="local human")
    approve.add_argument("--sample", action="store_true")
    reject = commands.add_parser("reject", help="Reject a candidate without changing the origin.")
    reject.add_argument("candidate_id")
    adopt = commands.add_parser("adopt", help="Prepare a layer-four candidate from a proposal.")
    adopt.add_argument("proposal_path", type=Path)
    commands.add_parser("derivability", help="Reject projection meaning absent from the origin.")
    commands.add_parser("attribution", help="Attribute pending change to origin or pins.")
    initialize = commands.add_parser("init", help="Initialize a new four-layer origin.")
    initialize.add_argument("path", type=Path)
    initialize.add_argument("--name", required=True)
    initialize.add_argument("--who", required=True)
    initialize.add_argument("--pain", required=True)
    initialize.add_argument("--journey", required=True)
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
    if args.command == "showcase":
        serve_showcase(root, args.host, args.port)
        return 0
    if args.command == "preview":
        candidate = prepare_candidate(
            root, args.layer_file, args.candidate_path.resolve().read_text(encoding="utf-8")
        )
        print(f"candidate {candidate.candidate_id}: {'valid' if candidate.valid else 'blocked'}")
        print("changed: " + ", ".join(candidate.changed_records))
        print("affected records: " + ", ".join(candidate.affected_records))
        print("affected projections: " + ", ".join(candidate.affected_projections))
        for issue in candidate.errors + candidate.warnings:
            print(f"issue: {issue}")
        for bet in candidate.blocked_by_losing_records:
            print(f"losing record: {bet}")
        return 0 if candidate.valid else 1
    if args.command == "approve":
        provider = SampleContentProvider() if args.sample else OpenAIContentProvider()
        result = approve_candidate(root, args.candidate_id, provider, approved_by=args.approved_by)
        print(f"approved: projection {result.projection_digest[:12]}")
        print(result.history_path)
        return 0
    if args.command == "reject":
        reject_candidate(root, args.candidate_id)
        print(f"rejected: {args.candidate_id}")
        return 0
    if args.command == "adopt":
        candidate = candidate_from_proposal(root, args.proposal_path.resolve())
        print(f"candidate {candidate.candidate_id}: {'valid' if candidate.valid else 'blocked'}")
        return 0 if candidate.valid else 1
    if args.command == "derivability":
        derivability_report = check_projection_derivability(root)
        if derivability_report.valid:
            print("Every projection is derivable from the approved origin and pins.")
            return 0
        print("Unsupported projection changes:")
        for path in derivability_report.unsupported:
            print(f"- {path}")
        return 1
    if args.command == "attribution":
        attribution = attribute_change(root)
        print(f"pending change: {attribution.cause}")
        return 0
    if args.command == "init":
        destination = args.path.resolve()
        initialize_workspace(
            destination,
            name=args.name,
            who=args.who,
            pain=args.pain,
            journey=args.journey,
        )
        print(f"Initialized valid origin: {destination}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
