from __future__ import annotations

from pathlib import Path

import yaml

from dodai.origin import load_origin, validate_origin
from dodai.projection import ProjectionContent, ProjectionEngine
from dodai.workspace import initialize_workspace


class ProductProvider:
    def __init__(self, product_name: str, headline: str) -> None:
        self.product_name = product_name
        self.headline = headline

    def derive(self, origin_text: str) -> ProjectionContent:
        return ProjectionContent(
            product_name=self.product_name,
            audience="Accountable product teams",
            headline=self.headline,
            value_proposition="Keep one meaning across roles.",
            call_to_action="Review the outcome",
            stakeholder_summary=f"{self.product_name} keeps its own intent isolated.",
        )


def test_two_different_products_use_the_same_origin_discipline(tmp_path: Path) -> None:
    decisions = tmp_path / "decisions"
    incidents = tmp_path / "incidents"
    initialize_workspace(
        decisions,
        name="decision-foundation",
        who="A team accountable for product decisions.",
        pain="Decision intent and later explanations diverge.",
        journey="A person reviews one approved decision and its rationale.",
    )
    initialize_workspace(
        incidents,
        name="incident-foundation",
        who="A team learning from service incidents.",
        pain="Incident learning is lost between response and follow-up.",
        journey="A person reviews one incident lesson and its evidence.",
    )

    for root in (decisions, incidents):
        report = validate_origin(load_origin(root / "origin"))
        assert report.errors == []
        assert report.warnings == []

    ProjectionEngine(decisions, ProductProvider("Decision Foundation", "Decide once")).project()
    ProjectionEngine(incidents, ProductProvider("Incident Foundation", "Learn once")).project()

    decision_projection = (decisions / "projections/developer/experience.py").read_text()
    incident_projection = (incidents / "projections/developer/experience.py").read_text()
    assert "Decision Foundation" in decision_projection
    assert "Incident Foundation" not in decision_projection
    assert "Incident Foundation" in incident_projection
    assert "Decision Foundation" not in incident_projection
    assert (
        yaml.safe_load((decisions / "projections/manifest.yaml").read_text())["projection_kind"]
        == "brief"
    )
