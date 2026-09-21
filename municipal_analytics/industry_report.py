"""
industry_report.py
====================

Generates a structured, data-driven "industry trends" article (roughly
800-1,200 words) summarizing findings across the synthetic proprietary
database -- aggregate asset growth, fee compression, and notable
findings -- written in a professional municipal-advisory tone, the kind
of piece a firm might publish as thought leadership or circulate to
state clients.

All figures cited are computed directly from the synthetic database at
generation time, so the report is internally consistent with whatever
``ProgramDatabase`` instance is passed in.
"""

from __future__ import annotations

import statistics
from typing import Dict, List

from municipal_analytics.growth_projection import compute_historical_cagr, current_sustainability
from municipal_analytics.program_database import PROGRAM_TYPES, ProgramDatabase, ProgramRecord

TYPE_LABELS = {
    "529": "529 college savings",
    "ABLE": "ABLE",
    "retirement": "state-facilitated retirement savings",
}


def _asset_cagr(record: ProgramRecord) -> float:
    try:
        return compute_historical_cagr(record, "total_assets")
    except ValueError:
        return 0.0


def aggregate_growth_trends(database: ProgramDatabase) -> Dict[str, dict]:
    trends = {}
    for ptype in PROGRAM_TYPES:
        records = database.filter(program_type=ptype)
        if not records:
            continue
        trends[ptype] = {
            "program_count": len(records),
            "total_assets": sum(r.total_assets for r in records),
            "total_accounts": sum(r.number_of_accounts for r in records),
            "average_asset_cagr": statistics.mean(_asset_cagr(r) for r in records),
        }
    return trends


def fee_compression_analysis(database: ProgramDatabase) -> Dict[str, dict]:
    """Splits each program type's peer set into older- and newer-vintage
    cohorts by inception year and compares average expense ratios,
    surfacing whether newer programs are launching with lower fees."""
    results = {}
    for ptype in PROGRAM_TYPES:
        records = sorted(database.filter(program_type=ptype), key=lambda r: r.inception_year)
        if len(records) < 2:
            continue
        mid = len(records) // 2
        older, newer = records[:mid], records[mid:]
        older_avg = statistics.mean(r.average_expense_ratio_bps for r in older)
        newer_avg = statistics.mean(r.average_expense_ratio_bps for r in newer)
        results[ptype] = {
            "older_cohort_avg_bps": older_avg,
            "newer_cohort_avg_bps": newer_avg,
            "delta_bps": newer_avg - older_avg,
        }
    return results


def _largest_program(database: ProgramDatabase) -> ProgramRecord:
    return max(database.all(), key=lambda r: r.total_assets)


def _fastest_growing_segment(trends: Dict[str, dict]) -> str:
    return max(trends, key=lambda t: trends[t]["average_asset_cagr"])


def _scale_fee_relationship(database: ProgramDatabase) -> dict:
    records = database.all()
    median_assets = statistics.median(r.total_assets for r in records)
    large = [r for r in records if r.total_assets >= median_assets]
    small = [r for r in records if r.total_assets < median_assets]
    return {
        "large_avg_bps": statistics.mean(r.average_expense_ratio_bps for r in large) if large else 0.0,
        "small_avg_bps": statistics.mean(r.average_expense_ratio_bps for r in small) if small else 0.0,
        "median_assets": median_assets,
    }


def _sustainability_snapshot(database: ProgramDatabase) -> dict:
    records = database.all()
    assessments = [current_sustainability(r) for r in records if r.history]
    sustainable = sum(1 for a in assessments if a.is_sustainable)
    return {
        "sustainable_count": sustainable,
        "total_count": len(assessments),
        "sustainable_pct": (sustainable / len(assessments)) if assessments else 0.0,
    }


def notable_findings(database: ProgramDatabase, trends: Dict[str, dict]) -> List[str]:
    findings = []

    largest = _largest_program(database)
    findings.append(
        f"**Scale leader.** {largest.program_name} is the largest program in our tracked "
        f"universe at ${largest.total_assets:,.0f} in assets across {largest.number_of_accounts:,} "
        f"accounts, an average account balance of ${largest.average_account_balance:,.0f}, "
        f"illustrating the asset concentration that can build in a well-established "
        f"{TYPE_LABELS.get(largest.program_type, largest.program_type)} program over time."
    )

    fastest = _fastest_growing_segment(trends)
    findings.append(
        f"**Fastest-growing segment.** {TYPE_LABELS[fastest].capitalize()} programs are "
        f"compounding assets fastest across the segments we track, averaging "
        f"{trends[fastest]['average_asset_cagr']:.1%} annualized asset growth over their "
        "trailing history, consistent with a still-maturing category climbing from a "
        "smaller asset base."
    )

    scale = _scale_fee_relationship(database)
    delta = scale["small_avg_bps"] - scale["large_avg_bps"]
    direction = "lower" if delta > 0 else "higher"
    findings.append(
        "**Scale and fees move together.** Programs above the database's median asset size "
        f"(${scale['median_assets']:,.0f}) carry an average blended expense ratio of "
        f"{scale['large_avg_bps']:.1f} bps, versus {scale['small_avg_bps']:.1f} bps for "
        f"programs below that threshold -- larger programs run {abs(delta):.1f} bps "
        f"{direction} on average, a pattern consistent with the fixed-cost leverage larger "
        "asset pools provide."
    )

    sustainability = _sustainability_snapshot(database)
    findings.append(
        "**Sustainability is uneven.** Measured against each program's own fixed "
        "administrative cost base and current state administrative fee rate, "
        f"{sustainability['sustainable_count']} of {sustainability['total_count']} programs "
        f"({sustainability['sustainable_pct']:.0%}) currently generate enough AUM-based fee "
        "revenue to fully cover fixed overhead -- underscoring why enrollment growth, not "
        "just asset growth, remains a board-level priority for many programs."
    )

    return findings


def generate_industry_report(database: ProgramDatabase) -> str:
    trends = aggregate_growth_trends(database)
    fees = fee_compression_analysis(database)
    findings = notable_findings(database, trends)

    total_programs = len(database)
    total_assets = sum(r.total_assets for r in database)
    total_accounts = sum(r.number_of_accounts for r in database)

    growth_lines = []
    for ptype in PROGRAM_TYPES:
        if ptype not in trends:
            continue
        t = trends[ptype]
        growth_lines.append(
            f"- **{TYPE_LABELS[ptype].capitalize()}** programs ({t['program_count']} in our "
            f"database) hold ${t['total_assets']:,.0f} in combined assets across "
            f"{t['total_accounts']:,} accounts, and have grown assets at an average "
            f"{t['average_asset_cagr']:.1%} annualized rate over their trailing history."
        )

    fee_lines = []
    for ptype in PROGRAM_TYPES:
        if ptype not in fees:
            continue
        f = fees[ptype]
        trend_word = "declined" if f["delta_bps"] < 0 else "risen"
        fee_lines.append(
            f"- **{TYPE_LABELS[ptype].capitalize()}**: the newer half of the program cohort "
            f"(by inception year) carries an average blended expense ratio of "
            f"{f['newer_cohort_avg_bps']:.1f} bps, versus {f['older_cohort_avg_bps']:.1f} bps "
            f"for the older half -- average fees have {trend_word} by "
            f"{abs(f['delta_bps']):.1f} bps between vintage cohorts."
        )

    findings_block = "\n\n".join(f"{i + 1}. {text}" for i, text in enumerate(findings))

    report = f"""# State Program Industry Trends: A Data-Driven Snapshot

*A research note prepared from our firm's proprietary database of state-run 529 college
savings, ABLE, and retirement savings programs.*

## Executive Summary

Across the {total_programs} state programs in our proprietary tracking database, combined
assets under administration now total approximately ${total_assets:,.0f}, spread across
{total_accounts:,} participant accounts. This note summarizes what the data tells us about
three questions state boards, treasurers, and program managers consistently ask us: how fast
is the market growing, where are fees headed, and what should programs be watching most
closely heading into their next budget and vendor-review cycles. As always, our observations
here are descriptive of the market as we track it, not predictive guarantees for any single
program, and each program's specific facts and circumstances should be evaluated on their
own merits before any board or procurement decision is made.

## Asset Growth Across the Market

State-run savings programs continue to expand at meaningfully different rates depending on
program type and maturity. Our database shows the following by segment:

{chr(10).join(growth_lines)}

The pattern is broadly consistent with what we would expect from the lifecycle of each
program category. 529 programs, the oldest and most established segment we track, compound
from a much larger asset base and therefore show comparatively moderate percentage growth
even though their dollar-value growth is often the largest in absolute terms. ABLE programs,
which only became possible following the federal ABLE Act, and state-facilitated retirement
programs, most of which have launched within the last decade, are still in an enrollment
build-out phase; both segments post substantially higher annualized growth rates as new
employers and participants are onboarded each year. Boards overseeing newer programs should
expect this elevated growth to persist for several more years before it normalizes toward
the more moderate trajectory typical of mature 529 programs, and should size administrative
budgets and staffing accordingly rather than assuming today's growth rate is a steady state.

## The Fee Compression Story

A defining trend across the savings-program industry over the past decade has been the
steady compression of investment-option expense ratios, driven by broader adoption of
index-based and passively managed underlying funds. Comparing the older half of each
program type's cohort (by inception year) against the newer half, our database shows:

{chr(10).join(fee_lines)}

This vintage-cohort comparison is an imperfect substitute for tracking a single program's
fees over time, since it compares different programs rather than the same program's fee
schedule across years, but it is a reasonable proxy for the direction of travel across the
industry: newer program launches are generally able to negotiate leaner fee schedules out of
the gate, both because recordkeeping technology has become more efficient and because
passively managed investment options have become the default building block for
age-based and target-enrollment portfolios. Programs that have not refreshed their
investment menu or renegotiated their recordkeeping contract in several years should treat
this as a prompt to benchmark their current fee schedule against more recently launched
peers.

## Three Notable Findings From the Data

{findings_block}

## Outlook

Taken together, the data point to a market that is growing steadily but unevenly, with fee
pressure remaining a persistent theme regardless of program type. Programs that are able to
pair enrollment growth with disciplined fee management are best positioned to clear the
sustainability bar we calculate against fixed administrative costs; programs that are
growing assets but not accounts -- or that have not revisited pricing in several years -- are
the ones most likely to face a difficult budget conversation with their board in the next
cycle. We will continue to update this analysis as our proprietary database is refreshed
with new program filings, and we encourage program managers and state boards evaluating
their competitive position to reach out for a program-specific benchmarking review.
"""
    return report.strip()


def report_word_count(report: str) -> int:
    return len(report.split())


if __name__ == "__main__":
    from municipal_analytics.program_database import build_default_database

    db = build_default_database()
    report = generate_industry_report(db)
    print(report)
    print(f"\n\n[word count: {report_word_count(report)}]")
