import pytest

from municipal_analytics.growth_projection import (
    SCENARIOS,
    compute_historical_cagr,
    current_sustainability,
    full_growth_model,
    project_growth,
    required_assets_per_account,
    scenario_growth_rates,
    sustainability_analysis,
)
from municipal_analytics.program_database import HistoricalPoint, ProgramRecord


def _make_record(**overrides) -> ProgramRecord:
    defaults = dict(
        program_id="TEST",
        state="Test State",
        program_type="529",
        program_name="Test Plan",
        inception_year=2010,
        program_manager="Test Manager",
        total_assets=1_000_000.0,
        number_of_accounts=1000,
        investment_options=[],
        state_admin_fee_bps=5.0,
        fixed_admin_cost_annual=100_000.0,
        history=[
            HistoricalPoint(2020, 500_000.0, 500),
            HistoricalPoint(2025, 1_000_000.0, 1000),
        ],
    )
    defaults.update(overrides)
    return ProgramRecord(**defaults)


def test_cagr_matches_known_doubling_and_requires_two_points():
    # Assets exactly double over 5 years -> CAGR = 2**(1/5) - 1
    record = _make_record()
    cagr = compute_historical_cagr(record, "total_assets")
    assert cagr == pytest.approx(2 ** (1 / 5) - 1, rel=1e-6)

    single_point = _make_record(history=[HistoricalPoint(2025, 1_000_000.0, 1000)])
    with pytest.raises(ValueError):
        compute_historical_cagr(single_point)


def test_project_growth_structure_and_ordering():
    record = _make_record()

    rates = scenario_growth_rates(record)
    assert rates["conservative"]["asset_growth_rate"] < rates["base"]["asset_growth_rate"]
    assert rates["base"]["asset_growth_rate"] < rates["optimistic"]["asset_growth_rate"]

    projections = project_growth(record, years=5)

    assert set(projections.keys()) == set(SCENARIOS)
    for scenario in SCENARIOS:
        assert len(projections[scenario]) == 5

    years = [p.year for p in projections["base"]]
    assert years == [2026, 2027, 2028, 2029, 2030]

    conservative_final = projections["conservative"][-1].total_assets
    base_final = projections["base"][-1].total_assets
    optimistic_final = projections["optimistic"][-1].total_assets
    assert conservative_final <= base_final <= optimistic_final


def test_project_growth_empty_history_raises():
    record = _make_record(history=[])
    with pytest.raises(ValueError):
        project_growth(record)


def test_current_sustainability_flags_shortfall_and_surplus():
    # fee_rate = 0.001; required = 100_000 / 0.001 / accounts
    formula_record = _make_record(state_admin_fee_bps=10.0, fixed_admin_cost_annual=100_000.0)
    result = required_assets_per_account(formula_record, number_of_accounts=1000)
    assert result == pytest.approx(100_000 / 0.001 / 1000)

    zero_fee_record = _make_record(state_admin_fee_bps=0.0)
    assert required_assets_per_account(zero_fee_record, number_of_accounts=1000) == float("inf")

    shortfall_record = _make_record(
        total_assets=100_000.0,
        number_of_accounts=1000,
        state_admin_fee_bps=5.0,
        fixed_admin_cost_annual=10_000_000.0,
    )
    shortfall = current_sustainability(shortfall_record)
    assert shortfall.is_sustainable is False
    assert shortfall.surplus_or_deficit_per_account < 0

    surplus_record = _make_record(
        total_assets=100_000_000.0,
        number_of_accounts=100,
        state_admin_fee_bps=10.0,
        fixed_admin_cost_annual=1_000.0,
    )
    surplus = current_sustainability(surplus_record)
    assert surplus.is_sustainable is True
    assert surplus.surplus_or_deficit_per_account > 0


def test_full_growth_model_bundle():
    record = _make_record()
    model = full_growth_model(record)

    expected_keys = {
        "program_id",
        "historical_asset_cagr",
        "historical_account_cagr",
        "scenario_growth_rates",
        "projections",
        "current_sustainability",
        "projected_sustainability",
    }
    assert set(model.keys()) == expected_keys
    assert model["program_id"] == "TEST"

    sustainability_results = sustainability_analysis(record, model["projections"])
    assert set(sustainability_results.keys()) == set(SCENARIOS)
    for scenario in SCENARIOS:
        assert sustainability_results[scenario].year == model["projections"][scenario][-1].year
