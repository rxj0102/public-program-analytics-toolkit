"""
presentation_summary.py
=========================

Generates a slide-by-slide outline (10-12 slides) for a board
presentation summarizing a single program's performance, competitive
position, and growth outlook -- pulling figures directly from
``growth_projection`` and ``competitive_benchmarking`` rather than
restating numbers by hand, the way an analyst would build the deck
skeleton before dropping it into a slide template.

This module returns structured ``Slide`` objects (title + bullets)
rather than a rendered ``.pptx`` file, so it can be fed into whatever
slide-authoring tool or template the firm uses downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from municipal_analytics.competitive_benchmarking import BenchmarkReport, benchmark_program
from municipal_analytics.growth_projection import SCENARIOS, full_growth_model
from municipal_analytics.program_database import ProgramDatabase, ProgramRecord


def _ordinal(n: float) -> str:
    i = int(round(n))
    if 10 <= i % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(i % 10, "th")
    return f"{i}{suffix}"


@dataclass
class Slide:
    number: int
    title: str
    bullets: List[str] = field(default_factory=list)


def _overview_slide(number: int, program: ProgramRecord) -> Slide:
    return Slide(
        number=number,
        title="Program Overview",
        bullets=[
            f"Program: {program.program_name} ({program.program_type})",
            f"Program manager (recordkeeper): {program.program_manager}",
            f"Inception year: {program.inception_year}",
            f"Total assets: ${program.total_assets:,.0f}",
            f"Total accounts: {program.number_of_accounts:,}",
            f"Average account balance: ${program.average_account_balance:,.0f}",
        ],
    )


def _trends_slide(number: int, program: ProgramRecord, model: dict) -> Slide:
    recent_history = program.history[-3:] if len(program.history) >= 3 else program.history
    bullets = [
        f"Historical asset growth (CAGR): {model['historical_asset_cagr']:.1%}",
        f"Historical account growth (CAGR): {model['historical_account_cagr']:.1%}",
    ]
    for point in recent_history:
        bullets.append(
            f"FY{point.year}: ${point.total_assets:,.0f} in assets, "
            f"{point.number_of_accounts:,} accounts"
        )
    return Slide(number=number, title="Historical Enrollment & Asset Trends", bullets=bullets)


def _menu_fee_slide(number: int, program: ProgramRecord) -> Slide:
    categories = {}
    for option in program.investment_options:
        categories.setdefault(option.category, 0)
        categories[option.category] += 1
    bullets = [
        f"Total investment options: {program.number_of_investment_options}",
        f"Average expense ratio: {program.average_expense_ratio_bps:.1f} bps",
        f"State administrative fee: {program.state_admin_fee_bps:.1f} bps",
    ]
    for category, count in sorted(categories.items(), key=lambda kv: -kv[1]):
        bullets.append(f"  {category}: {count} option(s)")
    return Slide(number=number, title="Investment Menu & Fee Structure", bullets=bullets)


def _competitive_fees_menu_slide(number: int, benchmark: BenchmarkReport) -> Slide:
    bullets = [f"Peer group: {benchmark.peer_group_size} comparable programs"]
    for m in benchmark.metrics:
        if m.metric in ("average_expense_ratio_bps", "number_of_investment_options"):
            bullets.append(
                f"{m.label}: {m.program_value:.1f} (peer median {m.peer_median:.1f}) "
                f"-- {_ordinal(m.percentile_rank)} percentile"
            )
    return Slide(number=number, title="Competitive Positioning: Fees & Menu", bullets=bullets)


def _competitive_growth_slide(number: int, benchmark: BenchmarkReport) -> Slide:
    bullets = []
    for m in benchmark.metrics:
        if m.metric == "asset_cagr":
            bullets.append(
                f"5-year historical asset CAGR: {m.program_value:.1%} "
                f"(peer median {m.peer_median:.1%}) -- {_ordinal(m.percentile_rank)} percentile"
            )
    return Slide(number=number, title="Competitive Positioning: Asset Growth", bullets=bullets)


def _gaps_slide(number: int, benchmark: BenchmarkReport) -> Slide:
    bullets = [f"[{g.severity.upper()}] {g.description}" for g in benchmark.gaps]
    return Slide(number=number, title="Competitive Gaps & Advantages", bullets=bullets)


def _projection_slide(number: int, model: dict, years: int) -> Slide:
    bullets = []
    for scenario in SCENARIOS:
        final = model["projections"][scenario][-1]
        bullets.append(
            f"{scenario.capitalize()} ({final.year}, +{years}y): "
            f"${final.total_assets:,.0f} in assets, {final.number_of_accounts:,} accounts"
        )
    return Slide(number=number, title=f"{years}-Year Growth Projections", bullets=bullets)


def _sustainability_slide(number: int, model: dict) -> Slide:
    current = model["current_sustainability"]
    bullets = [
        f"Current status ({current.year}): "
        f"{'SUSTAINABLE' if current.is_sustainable else 'AT RISK'} "
        f"(avg balance ${current.projected_average_account_balance:,.0f} vs. "
        f"required ${current.required_assets_per_account:,.0f} to cover fixed admin costs)",
    ]
    for scenario in SCENARIOS:
        s = model["projected_sustainability"][scenario]
        bullets.append(
            f"{scenario.capitalize()} scenario ({s.year}): "
            f"{'SUSTAINABLE' if s.is_sustainable else 'AT RISK'} "
            f"(surplus/deficit per account: ${s.surplus_or_deficit_per_account:,.0f})"
        )
    return Slide(number=number, title="Sustainability Analysis", bullets=bullets)


def _recommendations_slide(
    number: int, benchmark: BenchmarkReport, model: dict
) -> Slide:
    bullets = []
    for g in benchmark.gaps:
        if g.severity == "gap":
            bullets.append(f"Address competitive gap: {g.label}")

    base_sustainability = model["projected_sustainability"]["base"]
    if not base_sustainability.is_sustainable:
        bullets.append(
            "Evaluate options to close the projected sustainability gap: accelerate "
            "enrollment/marketing spend, revisit the state administrative fee rate, or "
            "phase in targeted expense reductions."
        )
    else:
        bullets.append(
            "Base-case trajectory is sustainable; continue current enrollment and fee strategy."
        )

    if not bullets:
        bullets.append("No material gaps identified; maintain current strategy and monitoring cadence.")

    return Slide(number=number, title="Recommendations", bullets=bullets)


def _appendix_slide(number: int, program: ProgramRecord) -> Slide:
    return Slide(
        number=number,
        title="Appendix: Data Sources & Methodology",
        bullets=[
            "Figures sourced from the firm's internal proprietary industry database of "
            "comparable state programs.",
            "Growth projections derived from each program's own trailing historical CAGR, "
            "scaled for conservative/base/optimistic scenarios.",
            "Peer benchmarking limited to programs of the same program type "
            f"({program.program_type}).",
            "Sustainability metric compares projected average account balance to the "
            "balance required to cover fixed administrative costs at the program's current "
            "state administrative fee rate.",
        ],
    )


def generate_presentation_outline(
    program: ProgramRecord, database: ProgramDatabase, years: int = 5
) -> List[Slide]:
    """Build the full 12-slide board presentation outline for ``program``."""
    model = full_growth_model(program, years=years)
    benchmark = benchmark_program(program, database)

    slides: List[Slide] = []
    slides.append(
        Slide(
            number=1,
            title=f"{program.program_name}",
            bullets=[
                "Board Presentation: Program Performance & Outlook",
                f"Program type: {program.program_type}",
                f"State: {program.state}",
                f"As of: FY{program.history[-1].year}" if program.history else "",
            ],
        )
    )
    slides.append(
        Slide(
            number=2,
            title="Agenda",
            bullets=[
                "Program overview",
                "Historical enrollment & asset trends",
                "Investment menu & fee structure",
                "Competitive positioning",
                "Growth projections",
                "Sustainability analysis",
                "Recommendations",
            ],
        )
    )
    slides.append(_overview_slide(3, program))
    slides.append(_trends_slide(4, program, model))
    slides.append(_menu_fee_slide(5, program))
    slides.append(_competitive_fees_menu_slide(6, benchmark))
    slides.append(_competitive_growth_slide(7, benchmark))
    slides.append(_gaps_slide(8, benchmark))
    slides.append(_projection_slide(9, model, years))
    slides.append(_sustainability_slide(10, model))
    slides.append(_recommendations_slide(11, benchmark, model))
    slides.append(_appendix_slide(12, program))

    return slides


def render_outline_text(slides: List[Slide]) -> str:
    lines = []
    for slide in slides:
        lines.append(f"Slide {slide.number}: {slide.title}")
        for bullet in slide.bullets:
            if bullet:
                lines.append(f"  - {bullet}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    from municipal_analytics.program_database import build_default_database

    db = build_default_database()
    sample = db.filter(program_type="529")[0]
    slides = generate_presentation_outline(sample, db)
    print(render_outline_text(slides))
