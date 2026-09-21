from municipal_analytics.industry_report import (
    aggregate_growth_trends,
    fee_compression_analysis,
    generate_industry_report,
    notable_findings,
    report_word_count,
)


def test_aggregate_growth_trends_covers_all_types(database):
    trends = aggregate_growth_trends(database)
    assert set(trends.keys()) == {"529", "ABLE", "retirement"}
    for t in trends.values():
        assert t["program_count"] > 0
        assert t["total_assets"] > 0


def test_fee_compression_analysis_has_consistent_deltas(database):
    fees = fee_compression_analysis(database)
    for f in fees.values():
        assert f["delta_bps"] == f["newer_cohort_avg_bps"] - f["older_cohort_avg_bps"]


def test_notable_findings_returns_a_handful_of_findings(database):
    trends = aggregate_growth_trends(database)
    findings = notable_findings(database, trends)
    assert 2 <= len(findings) <= 4
    assert all(isinstance(f, str) and len(f) > 0 for f in findings)


def test_generate_industry_report_word_count_and_sections(database):
    report = generate_industry_report(database)
    word_count = report_word_count(report)
    assert 800 <= word_count <= 1200

    for heading in ("Executive Summary", "Asset Growth", "Fee Compression", "Notable Findings", "Outlook"):
        assert heading in report

    assert str(len(database)) in report
