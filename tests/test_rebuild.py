from __future__ import annotations

from pathlib import Path

from dodai.projection import ProjectionContent, ProjectionEngine
from dodai.rebuild import rebuild_and_compare


class FixedProvider:
    def derive(self, origin_text: str) -> ProjectionContent:
        return ProjectionContent(
            product_name="Signal List",
            audience="Product teams",
            headline="Keep intent aligned",
            value_proposition="Join the waitlist.",
            call_to_action="Join",
            stakeholder_summary="One shared product meaning.",
        )


def test_rebuild_reports_agreement_for_derivable_projections(project: Path) -> None:
    ProjectionEngine(project, FixedProvider()).project()

    result = rebuild_and_compare(project)

    assert result.matches is True
    assert result.differences == []


def test_rebuild_reports_a_projection_with_leaked_decision(project: Path) -> None:
    ProjectionEngine(project, FixedProvider()).project()
    brief = project / "projections/stakeholder/brief.md"
    brief.write_text(brief.read_text() + "\nA decision absent from the origin.\n")

    result = rebuild_and_compare(project)

    assert result.matches is False
    assert result.differences == ["stakeholder/brief.md"]
