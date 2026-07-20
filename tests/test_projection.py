from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from dodai.projection import ProjectionContent, ProjectionEngine, SampleContentProvider


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def derive(self, origin_text: str) -> ProjectionContent:
        self.calls += 1
        return ProjectionContent(
            product_name="Signal List",
            audience="Teams exploring origin-driven delivery",
            headline="Keep intent and delivery aligned",
            value_proposition="Join a small waitlist for early access.",
            call_to_action="Join the waitlist",
            stakeholder_summary="A minimal journey proving shared intent across roles.",
        )


def test_one_request_creates_both_role_projections(project: Path) -> None:
    provider = CountingProvider()

    result = ProjectionEngine(project, provider).project()

    assert result.changed is True
    assert (project / "projections/developer/waitlist.py").is_file()
    assert (project / "projections/developer/test_waitlist.py").is_file()
    assert (project / "projections/stakeholder/brief.md").is_file()
    generated_app = (project / "projections/developer/waitlist.py").read_text()
    assert "def create_application" in generated_app
    assert 'if __name__ == "__main__"' in generated_app
    assert provider.calls == 1


def test_projection_rejects_evidence_that_uses_valid_but_unrelated_origin_records(
    project: Path,
) -> None:
    mapping = {
        "presentations": [
            {
                "path": path,
                "role": role,
                "story": "story_method_micromanagement",
                "criterion": "ac_role_projections",
                "specification": "spec_two_roles_share_one_origin",
            }
            for path, role in (
                ("developer/waitlist.py", "developer"),
                ("developer/test_waitlist.py", "developer"),
                ("stakeholder/brief.md", "stakeholder"),
            )
        ]
    }
    mapping_path = project / "pins/presentation-map.yaml"
    mapping_path.parent.mkdir(parents=True)
    mapping_path.write_text(yaml.safe_dump(mapping), encoding="utf-8")

    with pytest.raises(ValueError, match="does not support story"):
        ProjectionEngine(project, CountingProvider()).project()


def test_unchanged_origin_restores_identical_projections_without_model_call(project: Path) -> None:
    first_provider = CountingProvider()
    engine = ProjectionEngine(project, first_provider)
    engine.project()
    before = {
        path.relative_to(project / "projections"): path.read_bytes()
        for path in (project / "projections").rglob("*")
        if path.is_file()
    }
    second_provider = CountingProvider()

    result = ProjectionEngine(project, second_provider).project()
    after = {
        path.relative_to(project / "projections"): path.read_bytes()
        for path in (project / "projections").rglob("*")
        if path.is_file()
    }

    assert result.changed is False
    assert after == before
    assert second_provider.calls == 0


def test_renderer_upgrade_reuses_approved_meaning_without_model_call(project: Path) -> None:
    first = CountingProvider()
    result = ProjectionEngine(project, first).project()
    current_cache = project / ".dodai/cache" / f"{result.digest}.yaml"
    previous_cache = project / ".dodai/cache/previous-renderer.yaml"
    current_cache.rename(previous_cache)
    manifest_path = project / "projections/manifest.yaml"
    manifest = manifest_path.read_text().replace(result.digest, "previous-renderer")
    manifest_path.write_text(manifest)
    second = CountingProvider()

    ProjectionEngine(project, second).project()

    assert second.calls == 0
    assert current_cache.exists()


def test_runtime_cache_does_not_make_an_unchanged_projection_look_changed(project: Path) -> None:
    provider = CountingProvider()
    engine = ProjectionEngine(project, provider)
    engine.project()
    runtime_cache = project / "projections/developer/__pycache__/waitlist.pyc"
    runtime_cache.parent.mkdir(parents=True)
    runtime_cache.write_bytes(b"local runtime artifact")

    result = engine.project()

    assert result.changed is False
    assert provider.calls == 1


def test_refresh_rederives_content_for_the_same_origin(project: Path) -> None:
    provider = CountingProvider()
    engine = ProjectionEngine(project, provider)
    engine.project()

    engine.project(refresh=True)

    assert provider.calls == 2


def test_generated_code_keeps_model_copy_within_reviewable_line_length(project: Path) -> None:
    class LongCopyProvider(CountingProvider):
        def derive(self, origin_text: str) -> ProjectionContent:
            content = super().derive(origin_text)
            return ProjectionContent(
                **{
                    **content.__dict__,
                    "value_proposition": "A long model-derived promise " * 12,
                }
            )

    ProjectionEngine(project, LongCopyProvider()).project()
    generated = (project / "projections/developer/waitlist.py").read_text()

    assert max(len(line) for line in generated.splitlines()) <= 100


def test_japanese_origin_content_produces_a_japanese_executable_experience(
    project: Path,
) -> None:
    class JapaneseProvider(CountingProvider):
        def derive(self, origin_text: str) -> ProjectionContent:
            self.calls += 1
            return ProjectionContent(
                product_name="地域イベント",
                audience="地域の参加者",
                headline="関心のある催しを見逃さない",
                value_proposition="参加意思を残し、後から確認できます。",
                call_to_action="参加する",
                stakeholder_summary="参加者が催しへ参加意思を残せる体験です。",
            )

    ProjectionEngine(project, JapaneseProvider()).project()
    generated = (project / "projections/developer/waitlist.py").read_text()

    assert 'HTML_LANGUAGE = "ja"' in generated
    assert 'EMAIL_LABEL = "メールアドレス"' in generated
    assert 'INVALID = "有効なメールアドレスを入力してください。"' in generated


def test_sample_provider_derives_visible_meaning_from_the_given_origin() -> None:
    source = """origin: sample
who: 地域の参加者
statement: 参加意思を後から確認できる。
product_name: 地域イベント案内
journey: 価値を理解し、参加意思を残す。
"""

    content = SampleContentProvider().derive(source)

    assert content.product_name == "地域イベント案内"
    assert content.audience == "地域の参加者"
    assert content.headline == "参加意思を後から確認できる。"
    assert content.value_proposition == "価値を理解し、参加意思を残す。"
    assert content.call_to_action == "参加意思を残す"
