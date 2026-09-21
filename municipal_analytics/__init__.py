"""
municipal_analytics
====================

A toolkit that models the research and analysis workflow of a municipal
advisory analyst covering state-run investment programs: 529 college
savings plans, ABLE (disability savings) plans, and state-sponsored
retirement savings programs (e.g. auto-IRA "Secure Choice" programs).

ALL DATA IN THIS PACKAGE IS SYNTHETIC. Program names, asset totals,
account counts, fee schedules, and recordkeeper ("program manager")
names are randomly generated for demonstration purposes and do not
describe any real state program, vendor, or filing. See the project
README for full methodology notes.
"""

from municipal_analytics.program_database import (
    ProgramDatabase,
    ProgramRecord,
    InvestmentOption,
    HistoricalPoint,
)

__all__ = [
    "ProgramDatabase",
    "ProgramRecord",
    "InvestmentOption",
    "HistoricalPoint",
]

__version__ = "0.1.0"
