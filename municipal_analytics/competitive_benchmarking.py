"""
competitive_benchmarking.py
=============================

Benchmarks a single state program against its peer group in the
"proprietary database" on fees, investment menu breadth, and asset
growth rate -- the kind of comparative exhibit a municipal advisory
analyst builds ahead of a board update or an RFP response ("here is
where your program stands relative to the market").

Percentile convention
----------------------
For every metric, a higher percentile always means "more competitively
positioned," even when a *lower* raw value is better (e.g. fees). A
program at the 90th percentile on expense ratio means its fees are
lower than 90% of its peer group, not that its fees are higher.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from municipal_analytics.growth_projection import compute_historical_cagr
from municipal_analytics.program_database import ProgramDatabase, ProgramRecord

METRICS_HIGHER_IS_BETTER = {
    "average_expense_ratio_bps": False,
    "number_of_investment_options": True,
    "asset_cagr": True,
}

METRIC_LABELS = {
    "average_expense_ratio_bps": "Average expense ratio (bps)",
    "number_of_investment_options": "Investment menu breadth (# options)",
    "asset_cagr": "5-Year historical asset growth rate (CAGR)",
}


@dataclass
class MetricBenchmark:
    metric: str
    label: str
    program_value: float
    peer_median: float
    peer_mean: float
    percentile_rank: float  # 0-100, higher = more competitive
    higher_is_better: bool


@dataclass
class CompetitiveGap:
    metric: str
    label: str
    description: str
    severity: str  # "gap" | "advantage" | "in-line"


@dataclass
class BenchmarkReport:
    program_id: str
    program_name: str
    peer_group_size: int
    metrics: List[MetricBenchmark]
    gaps: List[CompetitiveGap]


def percentile_rank(
    peer_values: List[float], value: float, higher_is_better: bool = True
) -> float:
    """Percentile of ``value`` within ``peer_values`` (which should
    exclude the program's own value), expressed 0-100, where a higher
    percentile always means "more competitive" per ``higher_is_better``.

    Uses the standard "percentage of peers strictly worse than this
    value" convention, so a value tied with the best possible peer set
    still yields a percentile just under 100 rather than exactly 100
    unless it is literally better than every peer.
    """
    if not peer_values:
        return 50.0

    if higher_is_better:
        worse_count = sum(1 for v in peer_values if v < value)
    else:
        worse_count = sum(1 for v in peer_values if v > value)

    return round(100 * worse_count / len(peer_values), 1)


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _safe_asset_cagr(record: ProgramRecord) -> float:
    try:
        return compute_historical_cagr(record, "total_assets")
    except ValueError:
        return 0.0


def _metric_value(record: ProgramRecord, metric: str) -> float:
    if metric == "average_expense_ratio_bps":
        return record.average_expense_ratio_bps
    if metric == "number_of_investment_options":
        return record.number_of_investment_options
    if metric == "asset_cagr":
        return _safe_asset_cagr(record)
    raise ValueError(f"Unknown metric {metric!r}")


def benchmark_program(
    program: ProgramRecord,
    database: ProgramDatabase,
    peers: Optional[List[ProgramRecord]] = None,
) -> BenchmarkReport:
    """Benchmark ``program`` against same-program-type peers in
    ``database`` (or an explicit ``peers`` list) across fees, menu
    breadth, and asset growth."""
    peer_records = peers if peers is not None else database.peer_group(program)

    metrics: List[MetricBenchmark] = []
    for metric, higher_is_better in METRICS_HIGHER_IS_BETTER.items():
        program_value = _metric_value(program, metric)
        peer_values = [_metric_value(p, metric) for p in peer_records]

        metrics.append(
            MetricBenchmark(
                metric=metric,
                label=METRIC_LABELS[metric],
                program_value=program_value,
                peer_median=_median(peer_values),
                peer_mean=_mean(peer_values),
                percentile_rank=percentile_rank(peer_values, program_value, higher_is_better),
                higher_is_better=higher_is_better,
            )
        )

    gaps = identify_competitive_gaps(metrics)

    return BenchmarkReport(
        program_id=program.program_id,
        program_name=program.program_name,
        peer_group_size=len(peer_records),
        metrics=metrics,
        gaps=gaps,
    )


def identify_competitive_gaps(
    metrics: List[MetricBenchmark], gap_threshold: float = 35.0, advantage_threshold: float = 65.0
) -> List[CompetitiveGap]:
    """Translate percentile rankings into plain-language competitive
    gaps or advantages. A percentile below ``gap_threshold`` is flagged
    as a competitive gap; above ``advantage_threshold`` as an advantage;
    otherwise "in-line" with peers."""
    gaps: List[CompetitiveGap] = []
    for m in metrics:
        if m.metric == "average_expense_ratio_bps":
            diff = m.program_value - m.peer_median
            direction = "above" if diff > 0 else "below"
            detail = (
                f"{m.label} is {abs(diff):.1f} bps {direction} the peer median "
                f"({m.program_value:.1f} bps vs. {m.peer_median:.1f} bps)."
            )
        elif m.metric == "number_of_investment_options":
            diff = m.program_value - m.peer_median
            direction = "more than" if diff > 0 else "fewer than"
            detail = (
                f"{m.label}: {m.program_value:.0f} options vs. peer median "
                f"{m.peer_median:.0f} ({abs(diff):.0f} {direction} peer median)."
            )
        else:  # asset_cagr
            diff = m.program_value - m.peer_median
            direction = "above" if diff > 0 else "below"
            detail = (
                f"{m.label}: {m.program_value:.2%} vs. peer median {m.peer_median:.2%} "
                f"({abs(diff):.2%} {direction} peer median)."
            )

        if m.percentile_rank < gap_threshold:
            severity = "gap"
        elif m.percentile_rank > advantage_threshold:
            severity = "advantage"
        else:
            severity = "in-line"

        gaps.append(
            CompetitiveGap(
                metric=m.metric,
                label=m.label,
                description=detail,
                severity=severity,
            )
        )
    return gaps


if __name__ == "__main__":
    from municipal_analytics.program_database import build_default_database

    db = build_default_database()
    sample = db.filter(program_type="529")[0]
    report = benchmark_program(sample, db)
    print(f"Benchmark report for {report.program_name} ({report.program_id})")
    print(f"Peer group size: {report.peer_group_size}")
    for m in report.metrics:
        print(f"  {m.label}: {m.program_value:.2f} -> percentile {m.percentile_rank:.1f}")
    print("Competitive gaps / advantages:")
    for g in report.gaps:
        print(f"  [{g.severity:>8}] {g.description}")
