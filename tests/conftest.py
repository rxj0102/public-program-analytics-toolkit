import pytest

from municipal_analytics.program_database import ProgramDatabase


@pytest.fixture
def database() -> ProgramDatabase:
    """A deterministic synthetic database, fresh per test."""
    return ProgramDatabase.generate_synthetic(seed=42)


@pytest.fixture
def sample_529(database) -> "municipal_analytics.program_database.ProgramRecord":
    return database.filter(program_type="529")[0]


@pytest.fixture
def sample_able(database) -> "municipal_analytics.program_database.ProgramRecord":
    return database.filter(program_type="ABLE")[0]


@pytest.fixture
def sample_retirement(database) -> "municipal_analytics.program_database.ProgramRecord":
    return database.filter(program_type="retirement")[0]
