from __future__ import annotations

from pathlib import Path

from dodai.projection import ProjectionContent, ProjectionEngine


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
    assert provider.calls == 1


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


def test_refresh_rederives_content_for_the_same_origin(project: Path) -> None:
    provider = CountingProvider()
    engine = ProjectionEngine(project, provider)
    engine.project()

    engine.project(refresh=True)

    assert provider.calls == 2
