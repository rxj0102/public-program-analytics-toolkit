# public-program-analytics-toolkit

[![CI](https://github.com/rxj0102/public-program-analytics-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/rxj0102/public-program-analytics-toolkit/actions/workflows/ci.yml)

A Python toolkit that models the research and analysis workflow of a
**municipal advisory analyst** covering state-run investment programs:
529 college savings plans, ABLE (disability savings) plans, and
state-facilitated retirement savings programs (e.g. "Secure Choice"
auto-IRA programs).

## Scenario

Municipal advisory practices that serve state treasurers, program
managers (recordkeepers), and state boards typically maintain an
internal "proprietary database" of comparable state programs, which
they use to:

1. **Track the market** -- assets, accounts, fees, and investment
   menus across every comparable state program.
2. **Model a single program's trajectory** -- project asset and
   account growth under multiple scenarios, and assess whether the
   program can sustain its fixed administrative costs.
3. **Benchmark a client against peers** -- fees, investment menu
   breadth, and growth rate, with percentile rankings and specific
   competitive gaps.
4. **Respond to RFPs** -- when a state solicits proposals for program
   administration services, pull data-driven talking points straight
   from the database and growth model into a structured response.
5. **Publish market commentary** -- a data-driven "industry trends"
   note summarizing growth, fee compression, and notable findings.
6. **Brief the board** -- a slide-by-slide outline summarizing a
   program's performance, competitive position, and outlook, with
   numbers pulled directly from the underlying models.

This repository implements each of those six workflows as a standalone,
testable Python module, all built on top of one shared synthetic
database.

## ⚠️ All data is synthetic

**Every number in this repository is fabricated.** State names are
real (there are only 50 U.S. states, and using them is part of what
makes the toolkit realistic), but total assets, account counts, fee
schedules, inception years, and "program manager" (recordkeeper) names
are randomly generated within realistic ranges by
`program_database.ProgramDatabase.generate_synthetic()`. Program
manager names (e.g. "Meridian Trust Advisors") are **fictional firms
invented for this project** -- they do not refer to any real
recordkeeper, bank, or asset manager, and nothing in this repository
should be cited as real market data. Generation is seeded
(`seed=42` by default) so results are reproducible across runs.

## Project structure

```
municipal_analytics/
├── program_database.py         # Synthetic "proprietary database": 45 state program records
├── growth_projection.py        # 5-year, 3-scenario growth + sustainability model for one program
├── competitive_benchmarking.py # Percentile benchmarking of one program vs. its peer group
├── rfp_response_draft.py       # Structured draft response to a synthetic RFP
├── industry_report.py          # 800-1,200 word data-driven industry trends report
└── presentation_summary.py     # 10-12 slide board presentation outline

tests/                          # pytest suite (30 tests)
requirements.txt
pytest.ini
```

## Methodology

### 1. The proprietary database (`program_database.py`)

`ProgramDatabase.generate_synthetic()` builds 45 synthetic program
records (20 x 529, 15 x ABLE, 10 x retirement) spread across U.S.
states. Each `ProgramRecord` carries:

- `program_type`, `state`, `program_name`, `inception_year`
- `program_manager` (fictional recordkeeper)
- `total_assets`, `number_of_accounts` (and the derived
  `average_account_balance`)
- `investment_options`: a list of `InvestmentOption(name, category,
  expense_ratio_bps)` -- menu breadth and fee structure
- `state_admin_fee_bps` and `fixed_admin_cost_annual` -- inputs to the
  sustainability model
- `history`: 7 trailing fiscal years of assets and accounts, used to
  derive historical growth rates

Asset levels, account sizes, fee ranges, and inception-year windows
differ by program type to reflect real structural differences (529
programs are older and larger; ABLE and retirement programs are newer
and growing off a smaller base). Investment-option fees also carry a
**built-in fee-compression signal**: within each program type, newer
inception-year programs are generated with systematically lower
expense ratios, reflecting the industry's real shift toward
lower-cost, index-based investment menus.

`ProgramDatabase` supports `query`, `filter` (by type / state / manager
/ asset range), `peer_group`, `update` (in-place field updates,
mirroring "refreshing" a database record from a new filing), `add` /
`remove`, `summary_statistics`, and JSON `save` / `load`.

### 2. Growth & sustainability model (`growth_projection.py`)

Given a program's trailing history, `project_growth()` computes the
historical asset and account CAGR and projects 5 years forward under
three scenarios:

| Scenario | Growth rate multiplier vs. historical CAGR |
|---|---|
| Conservative | 0.6x |
| Base | 1.0x |
| Optimistic | 1.35x |

**Sustainability metric.** Many state programs fund fixed
administrative overhead (staff, board, marketing, outreach) that isn't
covered by the recordkeeper's per-account fee, via a small
basis-point "state administrative fee" assessed on total assets. Given
`fixed_admin_cost_annual` and `state_admin_fee_bps`, the *average
account balance a program needs* to fully cover that overhead is:

```
required_assets_per_account = fixed_admin_cost_annual
                               / (state_admin_fee_bps / 10_000)
                               / number_of_accounts
```

`sustainability_analysis()` compares this required balance to each
scenario's *projected* average account balance five years out, flagging
the program as sustainable or at risk under each growth path.

### 3. Competitive benchmarking (`competitive_benchmarking.py`)

`benchmark_program()` compares one program against all other programs
of the same type in the database on three metrics: average expense
ratio, investment menu breadth, and 5-year historical asset CAGR. Each
metric is converted to a 0-100 **percentile rank**, always oriented so
that a higher percentile means "more competitively positioned" (even
though a *lower* raw expense ratio is what's actually better).
`identify_competitive_gaps()` then translates those percentiles into
plain-language "gap" / "in-line" / "advantage" findings.

### 4. RFP response draft (`rfp_response_draft.py`)

`generate_rfp_response()` takes a synthetic `RFPRequest` (issuing state,
program type, key requirements, evaluation criteria) and produces the
five standard sections of an RFP response -- firm background
(placeholder), understanding of program needs, proposed approach,
relevant experience, and pricing framework -- pulling peer-group
medians, the firm's own tracked engagements, and (optionally) a
reference program's growth projection directly from the database and
growth model.

### 5. Industry trends report (`industry_report.py`)

`generate_industry_report()` aggregates the whole database into an
800-1,200 word markdown report covering asset growth trends by program
type, a fee-compression analysis (comparing older- vs. newer-vintage
cohorts within each program type), and three data-driven notable
findings (scale leader, fastest-growing segment, and a
sustainability snapshot across the database).

### 6. Board presentation outline (`presentation_summary.py`)

`generate_presentation_outline()` produces a 12-slide outline (title,
agenda, program overview, historical trends, menu & fees, two
competitive-positioning slides, competitive gaps, growth projections,
sustainability analysis, recommendations, and an appendix), calling
directly into `growth_projection` and `competitive_benchmarking` so
every number on the slides is generated, not hand-typed.

## Getting started

```bash
pip install -r requirements.txt

# Explore the synthetic database
python -m municipal_analytics.program_database

# Run each module's demo output
python -m municipal_analytics.growth_projection
python -m municipal_analytics.competitive_benchmarking
python -m municipal_analytics.rfp_response_draft
python -m municipal_analytics.industry_report
python -m municipal_analytics.presentation_summary

# Run the test suite
pytest -v
```

## Tests

The `tests/` directory contains 30 pytest tests covering:

- **Database logic**: generation determinism, query/filter/update/
  add/remove semantics, peer grouping, aggregate statistics, and JSON
  save/load round-trips.
- **Growth projection math**: CAGR calculation against a known
  doubling case, scenario growth-rate ordering, the sustainability
  formula against hand-computed expected values, and edge cases (a
  zero admin fee, a single historical data point).
- **Benchmarking percentiles**: `percentile_rank()` against manually
  computed expected percentiles for both "higher is better" and "lower
  is better" metrics, plus gap/advantage classification.
- **Generation modules**: structural checks on the RFP response
  sections, the industry report's word count and section headers, and
  the presentation outline's slide count and numbering -- each
  verified to actually reflect the underlying data rather than static
  text.

Run `pytest -v` from the repository root to execute the full suite.
