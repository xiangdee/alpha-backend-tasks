from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.briefing import Briefing

_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"


@dataclass
class MetricViewModel:
    name: str
    value: str


@dataclass
class BriefingReportViewModel:
    report_title: str
    company_name: str
    ticker: str
    sector: str
    analyst_name: str
    summary: str
    recommendation: str
    key_points: list[str]
    risks: list[str]
    metrics: list[MetricViewModel]
    generated_at: str
    created_at: str


class BriefingReportFormatter:
    """
    Transforms a stored Briefing ORM record into a report view model
    and renders it as HTML via a Jinja2 template.

    Concerns handled here (not in the route or template):
    - Sorting points by display_order
    - Grouping key_points vs risks
    - Normalising metric label capitalisation
    - Constructing a human-readable report title
    - Formatting timestamps for display
    """

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(
                enabled_extensions=("html", "xml"), default_for_string=True
            ),
        )

    def build_view_model(self, briefing: Briefing) -> BriefingReportViewModel:
        sorted_points = sorted(briefing.points, key=lambda p: p.display_order)

        key_points = [p.content for p in sorted_points if p.point_type == "key_point"]
        risks = [p.content for p in sorted_points if p.point_type == "risk"]

        sorted_metrics = sorted(briefing.metrics, key=lambda m: m.display_order)
        metrics = [
            MetricViewModel(name=self._normalise_label(m.name), value=m.value)
            for m in sorted_metrics
        ]

        return BriefingReportViewModel(
            report_title=f"Briefing Report — {briefing.company_name} ({briefing.ticker})",
            company_name=briefing.company_name,
            ticker=briefing.ticker,
            sector=briefing.sector,
            analyst_name=briefing.analyst_name,
            summary=briefing.summary,
            recommendation=briefing.recommendation,
            key_points=key_points,
            risks=risks,
            metrics=metrics,
            generated_at=self._format_ts(briefing.generated_at or datetime.now(timezone.utc)),
            created_at=self._format_ts(briefing.created_at),
        )

    def render_html(self, briefing: Briefing) -> str:
        vm = self.build_view_model(briefing)
        template = self._env.get_template("briefing_report.html")
        return template.render(report=vm)

    @staticmethod
    def _normalise_label(label: str) -> str:
        """Title-case each word in a metric label for consistent display."""
        return label.strip().title()

    @staticmethod
    def _format_ts(dt: datetime) -> str:
        return dt.strftime("%d %b %Y, %H:%M UTC")