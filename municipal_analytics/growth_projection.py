"""
growth_projection.py
=====================

Growth and sustainability modeling for a single state program, in the
style of the multi-scenario projections a municipal advisory analyst
would build ahead of a board meeting or an RFP response: given a
program's historical enrollment and asset trend, project asset and
account growth five years forward under base, optimistic, and
conservative scenarios, and evaluate whether the program is on a
sustainable trajectory relative to its fixed administrative costs.

Sustainability methodology
---------------------------
Many state programs fund fixed administrative costs (board and staff
overhead, marketing, outreach, compliance) that are not covered by the
recordkeeper's per-account fee, using a small basis-point "state
administrative fee" assessed on total assets. Given:

    fixed_admin_cost_annual  -- the program's fixed annual overhead ($)
    state_admin_fee_bps      -- the bps fee assessed on AUM to fund it

the annual revenue available to cover that overhead is::

    admin_revenue = total_assets * (state_admin_fee_bps / 10_000)

and the **required assets-per-account** the program needs to sustain,
given a projected account count, in order to fully cover fixed costs is::

    required_assets_per_account = fixed_admin_cost_annual
                                   / (state_admin_fee_bps / 10_000)
                                   / number_of_accounts

Comparing that figure to the *projected* average account balance under
each scenario flags whether the program is tracking toward a sustainable
asset base or is at risk of being unable to cover fixed overhead from
its own AUM-based fee revenue.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from municipal_analytics.program_database import ProgramRecord

SCENARIOS = ("conservative", "base", "optimistic")

# Multiplicative adjustments applied to the historically observed CAGR
# to derive scenario-specific growth rates.
_SCENARIO_ADJUSTMENTS = {
    "conservative": 0.6,
    "base": 1.0,
    "optimistic": 1.35,
}

DEFAULT_PROJECTION_YEARS = 5


@dataclass
class YearProjection:
    year: int
    total_assets: float
    number_of_accounts: int
    average_account_balance: float


@dataclass
class SustainabilityAssessment:
    scenario: str
    year: int
    projected_average_account_balance: float
    required_assets_per_account: float
    surplus_or_deficit_per_account: float
    is_sustainable: bool


def compute_historical_cagr(record: ProgramRecord, field_name: str = "total_assets") -> float:
    """Compound annual growth rate implied by a record's trailing history
    for either ``total_assets`` or ``number_of_accounts``."""
    if len(record.history) < 2:
        raise ValueError("Need at least two historical data points to compute CAGR")

    start = getattr(record.history[0], field_name)
    end = getattr(record.history[-1], field_name)
    years = record.history[-1].year - record.history[0].year

    if start <= 0 or years <= 0:
        return 0.0
    return (end / start) ** (1 / years) - 1


def scenario_growth_rates(record: ProgramRecord) -> Dict[str, Dict[str, float]]:
    """Base/optimistic/conservative asset and account growth rates,
    derived from the record's own historical CAGR."""
    base_asset_cagr = compute_historical_cagr(record, "total_assets")
    base_account_cagr = compute_historical_cagr(record, "number_of_accounts")

    rates: Dict[str, Dict[str, float]] = {}
    for scenario, multiplier in _SCENARIO_ADJUSTMENTS.items():
        rates[scenario] = {
            "asset_growth_rate": base_asset_cagr * multiplier,
            "account_growth_rate": base_account_cagr * multiplier,
        }
    return rates


def project_growth(
    record: ProgramRecord, years: int = DEFAULT_PROJECTION_YEARS
) -> Dict[str, List[YearProjection]]:
    """Project asset and account totals ``years`` into the future under
    each of the three scenarios, starting from the program's latest
    historical data point."""
    if not record.history:
        raise ValueError("Record has no historical data to project from")

    start_year = record.history[-1].year
    start_assets = record.history[-1].total_assets
    start_accounts = record.history[-1].number_of_accounts

    rates = scenario_growth_rates(record)
    projections: Dict[str, List[YearProjection]] = {}

    for scenario in SCENARIOS:
        asset_rate = rates[scenario]["asset_growth_rate"]
        account_rate = rates[scenario]["account_growth_rate"]

        series: List[YearProjection] = []
        assets = start_assets
        accounts = start_accounts
        for i in range(1, years + 1):
            assets = assets * (1 + asset_rate)
            accounts = max(accounts * (1 + account_rate), 1)
            series.append(
                YearProjection(
                    year=start_year + i,
                    total_assets=round(assets, 2),
                    number_of_accounts=int(round(accounts)),
                    average_account_balance=round(assets / accounts, 2),
                )
            )
        projections[scenario] = series

    return projections


def required_assets_per_account(record: ProgramRecord, number_of_accounts: int) -> float:
    """The average account balance the program needs, at its current
    state administrative fee rate, to fully fund fixed admin costs from
    AUM-based fee revenue given a projected account count."""
    if record.state_admin_fee_bps <= 0 or number_of_accounts <= 0:
        return float("inf")
    fee_rate = record.state_admin_fee_bps / 10_000
    return record.fixed_admin_cost_annual / fee_rate / number_of_accounts


def sustainability_analysis(
    record: ProgramRecord, projections: Dict[str, List[YearProjection]]
) -> Dict[str, SustainabilityAssessment]:
    """Evaluate, for the final projected year of each scenario, whether
    the projected average account balance is sufficient to cover fixed
    administrative costs at the program's current admin fee rate."""
    results: Dict[str, SustainabilityAssessment] = {}
    for scenario, series in projections.items():
        final = series[-1]
        needed = required_assets_per_account(record, final.number_of_accounts)
        surplus = final.average_account_balance - needed
        results[scenario] = SustainabilityAssessment(
            scenario=scenario,
            year=final.year,
            projected_average_account_balance=final.average_account_balance,
            required_assets_per_account=round(needed, 2) if needed != float("inf") else needed,
            surplus_or_deficit_per_account=round(surplus, 2) if needed != float("inf") else float("inf"),
            is_sustainable=surplus >= 0,
        )
    return results


def current_sustainability(record: ProgramRecord) -> SustainabilityAssessment:
    """Sustainability assessment as of the program's latest historical
    data point (i.e. today), rather than a future projection."""
    needed = required_assets_per_account(record, record.number_of_accounts)
    surplus = record.average_account_balance - needed
    return SustainabilityAssessment(
        scenario="current",
        year=record.history[-1].year if record.history else 0,
        projected_average_account_balance=round(record.average_account_balance, 2),
        required_assets_per_account=round(needed, 2) if needed != float("inf") else needed,
        surplus_or_deficit_per_account=round(surplus, 2) if needed != float("inf") else float("inf"),
        is_sustainable=surplus >= 0,
    )


def full_growth_model(record: ProgramRecord, years: int = DEFAULT_PROJECTION_YEARS) -> dict:
    """Convenience bundle used by downstream modules (RFP drafts,
    presentation outlines): historical CAGR, scenario projections, and
    sustainability findings all in one call."""
    projections = project_growth(record, years=years)
    return {
        "program_id": record.program_id,
        "historical_asset_cagr": compute_historical_cagr(record, "total_assets"),
        "historical_account_cagr": compute_historical_cagr(record, "number_of_accounts"),
        "scenario_growth_rates": scenario_growth_rates(record),
        "projections": projections,
        "current_sustainability": current_sustainability(record),
        "projected_sustainability": sustainability_analysis(record, projections),
    }


if __name__ == "__main__":
    from municipal_analytics.program_database import build_default_database

    db = build_default_database()
    sample = db.filter(program_type="529")[0]
    model = full_growth_model(sample)
    print(f"Growth model for {sample.program_name} ({sample.program_id})")
    print(f"  Historical asset CAGR: {model['historical_asset_cagr']:.2%}")
    for scenario in SCENARIOS:
        final = model["projections"][scenario][-1]
        sustainability = model["projected_sustainability"][scenario]
        print(
            f"  [{scenario:>12}] {final.year}: "
            f"${final.total_assets:,.0f} AUM, {final.number_of_accounts:,} accounts, "
            f"sustainable={sustainability.is_sustainable}"
        )
