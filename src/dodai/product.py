from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock
from typing import Any

import yaml

from dodai.origin import load_origin, validate_origin
from dodai.projection import ProjectionEngine

SOLUTION_TERMS = (
    "API",
    "CLI",
    "dashboard",
    "database",
    "framework",
    "server",
    "アプリ",
    "ダッシュボード",
    "データベース",
    "API",
)

DEFAULT_REGENERATION_SECONDS = 120
DEFAULT_UNSUCCESSFUL_REVISIONS = 3


@dataclass(frozen=True)
class ProductBet:
    project_id: str
    name: str
    stage: str
    actor: str = ""
    pain: str = ""
    outcome: str = ""
    guardrail_seconds: int = DEFAULT_REGENERATION_SECONDS
    exit_revisions: int = DEFAULT_UNSUCCESSFUL_REVISIONS
    journey: str = ""
    pending_solution: str = ""
    error: str = ""
    model_requests: int = 0
    pending_candidate: str = ""
    pending_layer: str = ""
    term_name: str = ""
    term_definition: str = ""
    verification_status: str = "not_run"
    pending_proposal: str = ""


@dataclass(frozen=True)
class GenerationPlan:
    cache_hit: bool
    maximum_requests: int
    maximum_cost_usd: float
    projections: tuple[str, ...]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:32] or "product-bet"


class ProductStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / ".dodai" / "workspaces"
        self._lock = RLock()

    def list(self) -> list[ProductBet]:
        if not self.directory.exists():
            return []
        return [self.load(path.stem) for path in sorted(self.directory.glob("*.yaml"))]

    def create(self, name: str) -> ProductBet:
        normalized = name.strip()
        if not normalized:
            raise ValueError("プロダクト名を入力してください。")
        suffix = sha256(normalized.encode()).hexdigest()[:6]
        project_id = f"{_slug(normalized)}-{suffix}"
        if self.state_path(project_id).exists():
            return self.load(project_id)
        bet = ProductBet(project_id=project_id, name=normalized, stage="problem")
        self.save(bet)
        return bet

    def state_path(self, project_id: str) -> Path:
        return self.directory / f"{project_id}.yaml"

    def workspace(self, project_id: str) -> Path:
        return self.directory / project_id

    def load(self, project_id: str) -> ProductBet:
        with self._lock:
            if re.fullmatch(r"[a-z0-9-]+", project_id) is None:
                raise ValueError("Invalid product bet identifier.")
            value = yaml.safe_load(self.state_path(project_id).read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("Product bet state must be a mapping.")
            return ProductBet(**value)

    def save(self, bet: ProductBet) -> None:
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            destination = self.state_path(bet.project_id)
            temporary = destination.with_suffix(".yaml.tmp")
            temporary.write_text(
                yaml.safe_dump(bet.__dict__, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            temporary.replace(destination)

    def update(self, project_id: str, **changes: object) -> ProductBet:
        with self._lock:
            current = self.load(project_id)
            values = {**current.__dict__, **changes}
            updated = ProductBet(**values)
            self.save(updated)
            return updated

    def claim_generation(self, project_id: str) -> ProductBet | None:
        with self._lock:
            current = self.load(project_id)
            if current.stage != "generation":
                return None
            return self.update(project_id, stage="generating", error="")


def solution_terms(text: str) -> list[str]:
    return [term for term in SOLUTION_TERMS if re.search(re.escape(term), text, re.I)]


def record_problem(
    store: ProductStore,
    project_id: str,
    *,
    actor: str,
    pain: str,
    intended_outcome: str = "",
) -> ProductBet:
    actor = actor.strip()
    pain = pain.strip()
    if not actor or not pain:
        raise ValueError("誰が、何に困っているかを入力してください。")
    prescribed = solution_terms(pain)
    if prescribed and not intended_outcome.strip():
        return store.update(
            project_id,
            actor=actor,
            pending_solution=", ".join(sorted(set(prescribed))),
            error="解決方法ではなく、それによって実現したい成果を教えてください。",
        )
    recovered_pain = (
        f"{actor}は、{intended_outcome.strip()}を実現できず困っている。" if prescribed else pain
    )
    return store.update(
        project_id,
        actor=actor,
        pain=recovered_pain,
        pending_solution="",
        error="",
        stage="outcomes",
    )


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    temporary.replace(path)


def record_outcomes(
    store: ProductStore,
    project_id: str,
    *,
    outcome: str,
    journey: str,
    guardrail_seconds: int | None = None,
    exit_revisions: int | None = None,
    term_name: str = "",
    term_definition: str = "",
) -> ProductBet:
    bet = store.load(project_id)
    active_guardrail_seconds = guardrail_seconds or bet.guardrail_seconds
    active_exit_revisions = exit_revisions or bet.exit_revisions
    if not outcome.strip() or not journey.strip():
        raise ValueError("成功した状態と、利用者が最初にして結果を得るまでを入力してください。")
    workspace = store.workspace(project_id)
    origin = workspace / "origin"
    terms = [
        {
            "id": "origin",
            "definition": "The sole authority for product intent and constraints.",
            "allowed_layers": [1, 2, 3, 4],
        },
        {
            "id": "projection",
            "definition": "A role-specific presentation derived from the origin.",
            "allowed_layers": [1, 2, 3, 4],
        },
    ]
    if term_name.strip() and term_definition.strip():
        terms.append(
            {
                "id": _slug(term_name),
                "definition": term_definition.strip(),
                "allowed_layers": [1, 2, 3, 4],
            }
        )
    _write(
        origin / "01-definitions.yaml",
        {
            "origin": project_id,
            "layer": {"number": 1, "name": "definitions"},
            "revision": 1,
            "terms": terms,
            "boundary_terms": {
                "story_solution_vocabulary": {
                    "forbidden_in": [2],
                    "examples": list(SOLUTION_TERMS),
                },
                "test_implementation_nouns": {
                    "forbidden_in": [4],
                    "examples": ["API", "database", "framework", "function", "table"],
                },
            },
        },
    )
    _write(
        origin / "02-user-stories.yaml",
        {
            "origin": project_id,
            "layer": {"number": 2, "name": "user_stories"},
            "revision": 1,
            "stories": [
                {
                    "id": "story_primary_pain",
                    "who": bet.actor,
                    "pain": bet.pain,
                    "losing_records": [],
                }
            ],
        },
    )
    criteria = [
        {
            "id": "ac_primary_outcome",
            "kind": "outcome",
            "supports": ["story_primary_pain"],
            "statement": outcome.strip(),
        },
        {
            "id": "guardrail_regeneration_budget",
            "kind": "guardrail",
            "supports": ["ac_primary_outcome"],
            "statement": "Complete regeneration remains practical during interactive use.",
            "measures": [
                {
                    "name": "elapsed_time",
                    "comparator": "less_than_or_equal_to",
                    "threshold": active_guardrail_seconds,
                    "unit": "seconds",
                },
                {
                    "name": "variable_model_cost",
                    "comparator": "less_than_or_equal_to",
                    "threshold": 1,
                    "unit": "USD",
                },
            ],
            "observation_scope": "One complete regeneration under documented conditions.",
        },
        {
            "id": "exit_origin_representation",
            "kind": "exit_condition",
            "supports": ["ac_primary_outcome"],
            "statement": "End this bet when repeated representation revisions do not converge.",
            "measure": {
                "name": "consecutive_unsuccessful_representation_revisions",
                "comparator": "greater_than_or_equal_to",
                "threshold": active_exit_revisions,
                "unit": "revisions",
            },
        },
    ]
    _write(
        origin / "03-acceptance-criteria.yaml",
        {
            "origin": project_id,
            "layer": {"number": 3, "name": "acceptance_criteria"},
            "revision": 1,
            "criteria": criteria,
        },
    )
    _write(
        origin / "04-test-specifications.yaml",
        {
            "origin": project_id,
            "layer": {"number": 4, "name": "test_specifications"},
            "revision": 1,
            "specifications": [],
        },
    )
    _write(
        workspace / "pins/projection.yaml",
        {"projection_kind": "waitlist", "product_name": bet.name, "journey": journey},
    )
    _write(
        workspace / "pins/presentation-map.yaml",
        {
            "presentations": [
                {
                    "path": path,
                    "role": role,
                    "story": "story_primary_pain",
                    "criterion": "ac_primary_outcome",
                    "specification": "spec_primary_outcome_is_observable",
                }
                for path, role in (
                    ("developer/waitlist.py", "developer"),
                    ("developer/test_waitlist.py", "developer"),
                    ("stakeholder/brief.md", "stakeholder"),
                )
            ]
        },
    )
    return store.update(
        project_id,
        outcome=outcome.strip(),
        guardrail_seconds=active_guardrail_seconds,
        exit_revisions=active_exit_revisions,
        journey=journey.strip(),
        term_name=term_name.strip(),
        term_definition=term_definition.strip(),
        stage="verification",
        error="",
    )


def propose_verification(store: ProductStore, project_id: str) -> list[dict[str, Any]]:
    bet = store.load(project_id)
    return [
        {
            "id": "spec_primary_outcome_is_observable",
            "verifies": ["ac_primary_outcome"],
            "given": f"{bet.actor} experiences the minimal product journey.",
            "when": "The complete journey is attempted under the declared conditions.",
            "then": bet.outcome,
        },
        {
            "id": "spec_regeneration_stays_within_budget",
            "verifies": ["guardrail_regeneration_budget"],
            "given": "The approved origin and reference conditions.",
            "when": "One complete regeneration is observed.",
            "then": "Elapsed time and variable model cost remain within the active thresholds.",
        },
        {
            "id": "spec_persistent_mismatch_ends_bet",
            "verifies": ["exit_origin_representation"],
            "given": "Observable mismatches remain after consecutive representation revisions.",
            "when": "The active unsuccessful-revision threshold is reached.",
            "then": "The current representation bet ends before another approach is pursued.",
        },
    ]


def approve_verification(store: ProductStore, project_id: str) -> ProductBet:
    workspace = store.workspace(project_id)
    path = workspace / "origin/04-test-specifications.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["specifications"] = propose_verification(store, project_id)
    _write(path, document)
    report = validate_origin(load_origin(workspace / "origin"))
    if not report.valid or report.warnings:
        raise ValueError("承認した原点が検証に合格しませんでした。")
    return store.update(project_id, stage="generation", error="")


def generation_plan(
    store: ProductStore, project_id: str, *, uses_external_model: bool = True
) -> GenerationPlan:
    workspace = store.workspace(project_id)
    engine = ProjectionEngine(workspace, _UnusedProvider())
    _, digest, _, _ = engine._source_and_digest()
    cache_hit = (workspace / ".dodai/cache" / f"{digest}.yaml").exists()
    return GenerationPlan(
        cache_hit=cache_hit,
        maximum_requests=0 if cache_hit or not uses_external_model else 1,
        maximum_cost_usd=0 if cache_hit or not uses_external_model else 1,
        projections=("動くプロダクトとテスト", "関係者向け説明"),
    )


class _UnusedProvider:
    def derive(self, origin_text: str) -> Any:
        raise AssertionError("Generation planning must not call a model provider.")


def verify_generated_projection(workspace: Path) -> bool:
    manifest = yaml.safe_load((workspace / "projections/manifest.yaml").read_text(encoding="utf-8"))
    filename = "experience.py" if manifest.get("projection_kind") == "brief" else "waitlist.py"
    path = workspace / "projections/developer" / filename
    spec = importlib.util.spec_from_file_location(f"dodai_verify_{workspace.name}", path)
    if spec is None or spec.loader is None:
        return False
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if manifest.get("projection_kind") == "brief":
        meaning = module.describe()
        return bool(meaning) and all(meaning.values())
    with TemporaryDirectory(prefix="dodai-product-verification-") as directory:
        records = Path(directory) / "registrations.json"
        try:
            first = module.register("person@example.com", records)
            duplicate = module.register("PERSON@example.com", records)
            try:
                module.register("invalid", records)
            except ValueError:
                invalid_rejected = True
            else:
                invalid_rejected = False
        except Exception:
            return False
    return first is True and duplicate is False and invalid_rejected
