from municipal_analytics.competitive_benchmarking import (
    MetricBenchmark,
    benchmark_program,
    identify_competitive_gaps,
    percentile_rank,
)


def test_percentile_rank_higher_is_better():
    # Strictly better than every peer -> 100th percentile.
    assert percentile_rank([1, 2, 3, 4], 5, higher_is_better=True) == 100.0
    # Strictly worse than every peer -> 0th percentile.
    assert percentile_rank([1, 2, 3, 4], 0, higher_is_better=True) == 0.0


def test_percentile_rank_lower_is_better_and_edge_cases():
    # For a "lower is better" metric (e.g. fees), the smallest value wins.
    assert percentile_rank([10, 20, 30], 5, higher_is_better=False) == 100.0
    assert percentile_rank([10, 20, 30], 40, higher_is_better=False) == 0.0

    assert percentile_rank([], 42, higher_is_better=True) == 50.0
    # value=25 beats 10 and 20 out of 5 peers -> 2/5 = 40.0
    assert percentile_rank([10, 20, 30, 40, 50], 25, higher_is_better=True) == 40.0


def test_benchmark_program_structure(database, sample_529):
    report = benchmark_program(sample_529, database)
    assert report.program_id == sample_529.program_id
    assert report.peer_group_size == len(database.filter(program_type="529")) - 1

    metric_names = {m.metric for m in report.metrics}
    assert metric_names == {
        "average_expense_ratio_bps",
        "number_of_investment_options",
        "asset_cagr",
    }
    for m in report.metrics:
        assert 0.0 <= m.percentile_rank <= 100.0

    assert len(report.gaps) == len(report.metrics)


def test_identify_competitive_gaps_classifies_severity():
    gap_metric = MetricBenchmark(
        metric="average_expense_ratio_bps",
        label="Average expense ratio (bps)",
        program_value=90.0,
        peer_median=30.0,
        peer_mean=30.0,
        percentile_rank=5.0,
        higher_is_better=False,
    )
    advantage_metric = MetricBenchmark(
        metric="number_of_investment_options",
        label="Investment menu breadth (# options)",
        program_value=40.0,
        peer_median=15.0,
        peer_mean=15.0,
        percentile_rank=95.0,
        higher_is_better=True,
    )
    gaps = identify_competitive_gaps([gap_metric, advantage_metric])
    assert gaps[0].severity == "gap"
    assert gaps[1].severity == "advantage"


def test_benchmark_program_explicit_peer_group_excludes_self(database, sample_529):
    peers = database.peer_group(sample_529)
    report = benchmark_program(sample_529, database, peers=peers)
    assert sample_529.program_id not in [p.program_id for p in peers]
    assert report.peer_group_size == len(peers)
