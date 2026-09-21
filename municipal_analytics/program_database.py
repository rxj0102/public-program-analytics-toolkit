"""
program_database.py
====================

Models a firm's "proprietary industry database" of state-run savings and
retirement programs -- the kind of internal tracker a municipal advisory
practice maintains on 529 college savings plans, ABLE plans, and
state-facilitated retirement savings programs so that it can benchmark
clients, respond to RFPs, and write industry commentary.

IMPORTANT -- SYNTHETIC DATA DISCLAIMER
---------------------------------------
Every record produced by ``ProgramDatabase.generate_synthetic`` is
fabricated. State names are real (there are only 50, and using
plausible sponsors is part of what makes the toolkit realistic), but
asset levels, account counts, fee schedules, inception years,
"program manager" (recordkeeper) names, and administrative cost figures
are randomly generated within realistic ranges. Program manager names
are fictional firms invented for this project -- they do not refer to
any real recordkeeper, bank, or asset manager. Nothing here should be
treated as, or cited as, real market data.

The module exposes a small in-memory "database" object (``ProgramDatabase``)
with query / filter / update / persistence operations, mirroring the
kind of internal tooling used to "update our proprietary industry
databases" after each research cycle.
"""

from __future__ import annotations

import json
import random
import statistics
from dataclasses import asdict, dataclass, field
from typing import Iterable, List, Optional

# ---------------------------------------------------------------------------
# Constants / reference data (synthetic but realistic labels)
# ---------------------------------------------------------------------------

PROGRAM_TYPES = ("529", "ABLE", "retirement")

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
]

# Fictional recordkeeper / program-manager firms invented for this project.
PROGRAM_MANAGERS = [
    "Meridian Trust Advisors",
    "Ascend Financial Services",
    "Beacon Hill Investment Partners",
    "Granite State Recordkeeping",
    "Cornerstone Capital Stewards",
    "Harbor Point Asset Services",
    "Prairie Sky Financial Group",
    "Summit Ridge Trust Company",
    "Bluewater Recordkeeping Solutions",
    "Ironwood Plan Administrators",
]

INVESTMENT_CATEGORIES = {
    # category -> (min_bps, max_bps)
    "Age-Based/Target Enrollment": (15, 55),
    "Static Asset Allocation": (12, 45),
    "Index Fund": (3, 15),
    "Actively Managed Fund": (35, 95),
    "FDIC-Insured/Stable Value": (0, 10),
    "Individual Fund Option": (20, 70),
}

_TYPE_PROFILE = {
    "529": {
        "name_suffix": "College Savings Plan",
        "inception_range": (1997, 2009),
        "assets_range": (3.0e8, 1.8e10),
        "avg_balance_range": (15_000, 32_000),
        "num_options_range": (8, 32),
        "fixed_admin_cost_range": (1_000_000, 15_000_000),
        "historical_asset_cagr_range": (0.08, 0.15),
        "historical_account_cagr_range": (0.02, 0.06),
        "count": 20,
    },
    "ABLE": {
        "name_suffix": "ABLE Savings Program",
        "inception_range": (2016, 2020),
        "assets_range": (5.0e6, 1.8e8),
        "avg_balance_range": (6_000, 16_000),
        "num_options_range": (3, 9),
        "fixed_admin_cost_range": (300_000, 3_000_000),
        "historical_asset_cagr_range": (0.15, 0.30),
        "historical_account_cagr_range": (0.08, 0.20),
        "count": 15,
    },
    "retirement": {
        "name_suffix": "Secure Choice Retirement Savings Program",
        "inception_range": (2017, 2023),
        "assets_range": (2.0e7, 2.5e9),
        "avg_balance_range": (800, 4_500),
        "num_options_range": (3, 7),
        "fixed_admin_cost_range": (500_000, 8_000_000),
        "historical_asset_cagr_range": (0.40, 0.90),
        "historical_account_cagr_range": (0.30, 0.70),
        "count": 10,
    },
}

HISTORY_YEARS = 7  # trailing fiscal years of history captured per program
LAST_HISTORICAL_YEAR = 2025


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class InvestmentOption:
    name: str
    category: str
    expense_ratio_bps: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HistoricalPoint:
    year: int
    total_assets: float
    number_of_accounts: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProgramRecord:
    program_id: str
    state: str
    program_type: str
    program_name: str
    inception_year: int
    program_manager: str
    total_assets: float
    number_of_accounts: int
    investment_options: List[InvestmentOption] = field(default_factory=list)
    state_admin_fee_bps: float = 0.0
    fixed_admin_cost_annual: float = 0.0
    history: List[HistoricalPoint] = field(default_factory=list)

    # -- derived properties -------------------------------------------------

    @property
    def number_of_investment_options(self) -> int:
        return len(self.investment_options)

    @property
    def average_expense_ratio_bps(self) -> float:
        if not self.investment_options:
            return 0.0
        return statistics.mean(o.expense_ratio_bps for o in self.investment_options)

    @property
    def average_account_balance(self) -> float:
        if self.number_of_accounts == 0:
            return 0.0
        return self.total_assets / self.number_of_accounts

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ProgramRecord":
        d = dict(d)
        d["investment_options"] = [
            InvestmentOption(**o) for o in d.get("investment_options", [])
        ]
        d["history"] = [HistoricalPoint(**h) for h in d.get("history", [])]
        return cls(**d)


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------


def _build_history(
    rng: random.Random,
    end_assets: float,
    end_accounts: int,
    asset_cagr: float,
    account_cagr: float,
    end_year: int = LAST_HISTORICAL_YEAR,
    years: int = HISTORY_YEARS,
) -> List[HistoricalPoint]:
    """Extrapolate backward from the current-year snapshot to build a
    plausible trailing history, with a little year-to-year noise so the
    series is not a perfectly smooth geometric curve."""
    points: List[HistoricalPoint] = []
    assets = end_assets
    accounts = end_accounts
    for offset in range(years):
        year = end_year - offset
        noise = rng.uniform(-0.03, 0.03)
        points.append(
            HistoricalPoint(
                year=year,
                total_assets=round(max(assets, 1.0), 2),
                number_of_accounts=max(int(accounts), 1),
            )
        )
        assets = assets / (1 + asset_cagr + noise)
        accounts = accounts / (1 + account_cagr + noise / 2)
    points.reverse()
    return points


def _build_investment_menu(
    rng: random.Random, num_options: int
) -> List[InvestmentOption]:
    options = []
    categories = list(INVESTMENT_CATEGORIES.keys())
    for i in range(num_options):
        category = rng.choice(categories)
        lo, hi = INVESTMENT_CATEGORIES[category]
        options.append(
            InvestmentOption(
                name=f"{category} Option {i + 1}",
                category=category,
                expense_ratio_bps=round(rng.uniform(lo, hi), 1),
            )
        )
    return options


def _generate_records(seed: int, counts: Optional[dict] = None) -> List[ProgramRecord]:
    rng = random.Random(seed)
    counts = counts or {t: _TYPE_PROFILE[t]["count"] for t in PROGRAM_TYPES}
    records: List[ProgramRecord] = []
    seq = 1

    for program_type in PROGRAM_TYPES:
        profile = _TYPE_PROFILE[program_type]
        n = counts.get(program_type, profile["count"])
        states = rng.sample(US_STATES, k=min(n, len(US_STATES)))
        # allow repeats if more programs requested than states available
        while len(states) < n:
            states.append(rng.choice(US_STATES))

        for state in states:
            assets = rng.uniform(*profile["assets_range"])
            avg_balance = rng.uniform(*profile["avg_balance_range"])
            accounts = max(int(assets / avg_balance), 1)
            asset_cagr = rng.uniform(*profile["historical_asset_cagr_range"])
            account_cagr = rng.uniform(*profile["historical_account_cagr_range"])
            num_options = rng.randint(*profile["num_options_range"])
            inception_year = rng.randint(*profile["inception_range"])

            # Fee compression signal: newer-vintage programs lean toward
            # lower-cost index-based menus than older-vintage programs,
            # mirroring the industry-wide shift toward passive investing.
            inc_lo, inc_hi = profile["inception_range"]
            vintage_span = max(inc_hi - inc_lo, 1)
            recency_frac = (inception_year - inc_lo) / vintage_span
            fee_compression_factor = 1.0 - 0.25 * recency_frac

            investment_options = _build_investment_menu(rng, num_options)
            for option in investment_options:
                option.expense_ratio_bps = round(
                    option.expense_ratio_bps * fee_compression_factor, 1
                )

            record = ProgramRecord(
                program_id=f"P{seq:03d}",
                state=state,
                program_type=program_type,
                program_name=f"{state} {profile['name_suffix']}",
                inception_year=inception_year,
                program_manager=rng.choice(PROGRAM_MANAGERS),
                total_assets=round(assets, 2),
                number_of_accounts=accounts,
                investment_options=investment_options,
                state_admin_fee_bps=round(rng.uniform(0, 12), 2),
                fixed_admin_cost_annual=round(
                    rng.uniform(*profile["fixed_admin_cost_range"]), 2
                ),
            )
            record.history = _build_history(
                rng,
                end_assets=record.total_assets,
                end_accounts=record.number_of_accounts,
                asset_cagr=asset_cagr,
                account_cagr=account_cagr,
            )
            # Keep the headline snapshot consistent with the latest
            # historical data point.
            record.total_assets = record.history[-1].total_assets
            record.number_of_accounts = record.history[-1].number_of_accounts

            records.append(record)
            seq += 1

    return records


# ---------------------------------------------------------------------------
# Database object
# ---------------------------------------------------------------------------


class ProgramDatabase:
    """An in-memory "proprietary database" of state program records with
    query, filter, update, and persistence helpers."""

    def __init__(self, records: Optional[Iterable[ProgramRecord]] = None):
        self._records: List[ProgramRecord] = list(records) if records else []

    # -- construction ---------------------------------------------------

    @classmethod
    def generate_synthetic(
        cls, seed: int = 42, counts: Optional[dict] = None
    ) -> "ProgramDatabase":
        """Build a fresh synthetic database. Deterministic for a given seed."""
        return cls(_generate_records(seed=seed, counts=counts))

    @classmethod
    def load(cls, path: str) -> "ProgramDatabase":
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return cls(ProgramRecord.from_dict(r) for r in raw)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([r.to_dict() for r in self._records], fh, indent=2)

    # -- basic access -----------------------------------------------------

    def all(self) -> List[ProgramRecord]:
        return list(self._records)

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(self._records)

    # -- query / filter ----------------------------------------------------

    def query(self, program_id: str) -> ProgramRecord:
        for r in self._records:
            if r.program_id == program_id:
                return r
        raise KeyError(f"No program with id {program_id!r}")

    def filter(
        self,
        program_type: Optional[str] = None,
        state: Optional[str] = None,
        manager: Optional[str] = None,
        min_assets: Optional[float] = None,
        max_assets: Optional[float] = None,
    ) -> List[ProgramRecord]:
        results = self._records
        if program_type is not None:
            results = [r for r in results if r.program_type == program_type]
        if state is not None:
            results = [r for r in results if r.state == state]
        if manager is not None:
            results = [r for r in results if r.program_manager == manager]
        if min_assets is not None:
            results = [r for r in results if r.total_assets >= min_assets]
        if max_assets is not None:
            results = [r for r in results if r.total_assets <= max_assets]
        return list(results)

    def peer_group(self, record: ProgramRecord) -> List[ProgramRecord]:
        """All records of the same program type, excluding ``record`` itself."""
        return [
            r
            for r in self._records
            if r.program_type == record.program_type
            and r.program_id != record.program_id
        ]

    # -- mutation ------------------------------------------------------------

    def add(self, record: ProgramRecord) -> None:
        if any(r.program_id == record.program_id for r in self._records):
            raise ValueError(f"Program id {record.program_id!r} already exists")
        self._records.append(record)

    def update(self, program_id: str, **fields) -> ProgramRecord:
        """Update one or more fields on a record in place, mirroring an
        analyst "refreshing" a proprietary database entry after new data
        comes in (e.g. an updated NAV report or fee schedule change)."""
        record = self.query(program_id)
        valid_fields = set(ProgramRecord.__dataclass_fields__.keys())
        for key, value in fields.items():
            if key not in valid_fields:
                raise ValueError(f"Unknown field {key!r} on ProgramRecord")
            setattr(record, key, value)
        return record

    def remove(self, program_id: str) -> None:
        record = self.query(program_id)
        self._records.remove(record)

    # -- aggregate stats -------------------------------------------------

    def summary_statistics(self) -> dict:
        if not self._records:
            return {
                "program_count": 0,
                "total_assets": 0.0,
                "total_accounts": 0,
                "by_type": {},
            }

        by_type = {}
        for program_type in PROGRAM_TYPES:
            group = [r for r in self._records if r.program_type == program_type]
            if not group:
                continue
            by_type[program_type] = {
                "program_count": len(group),
                "total_assets": round(sum(r.total_assets for r in group), 2),
                "total_accounts": sum(r.number_of_accounts for r in group),
                "average_expense_ratio_bps": round(
                    statistics.mean(r.average_expense_ratio_bps for r in group), 2
                ),
                "average_inception_year": round(
                    statistics.mean(r.inception_year for r in group), 1
                ),
            }

        return {
            "program_count": len(self._records),
            "total_assets": round(sum(r.total_assets for r in self._records), 2),
            "total_accounts": sum(r.number_of_accounts for r in self._records),
            "by_type": by_type,
        }


def build_default_database(seed: int = 42) -> ProgramDatabase:
    """Convenience factory used throughout the toolkit and its tests."""
    return ProgramDatabase.generate_synthetic(seed=seed)


if __name__ == "__main__":
    db = build_default_database()
    stats = db.summary_statistics()
    print(f"Generated {stats['program_count']} synthetic program records")
    print(f"Aggregate assets tracked: ${stats['total_assets']:,.0f}")
    for ptype, s in stats["by_type"].items():
        print(
            f"  {ptype:>10}: {s['program_count']:2d} programs, "
            f"${s['total_assets']:,.0f} AUM, "
            f"avg expense ratio {s['average_expense_ratio_bps']:.1f} bps"
        )
