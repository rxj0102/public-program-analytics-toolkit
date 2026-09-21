import os

import pytest

from municipal_analytics.program_database import (
    PROGRAM_TYPES,
    HistoricalPoint,
    InvestmentOption,
    ProgramDatabase,
    ProgramRecord,
)


def test_generated_database_structure(database):
    assert 40 <= len(database) <= 50

    ids = [r.program_id for r in database]
    assert len(ids) == len(set(ids)), "program ids must be unique"

    types_seen = {r.program_type for r in database}
    assert types_seen == set(PROGRAM_TYPES)

    for record in database:
        # Headline snapshot must stay consistent with the latest history point.
        assert record.total_assets == record.history[-1].total_assets
        assert record.number_of_accounts == record.history[-1].number_of_accounts
        # Derived properties must agree with the underlying fields.
        assert record.number_of_investment_options == len(record.investment_options)
        if record.number_of_accounts:
            assert record.average_account_balance == pytest.approx(
                record.total_assets / record.number_of_accounts
            )


def test_generation_is_deterministic_for_seed():
    db1 = ProgramDatabase.generate_synthetic(seed=42)
    db2 = ProgramDatabase.generate_synthetic(seed=42)
    assert [r.program_id for r in db1] == [r.program_id for r in db2]
    assert db1.all()[0].total_assets == db2.all()[0].total_assets


def test_query_found_and_not_found(database):
    target = database.all()[0]
    assert database.query(target.program_id).program_id == target.program_id
    with pytest.raises(KeyError):
        database.query("NOT-A-REAL-ID")


def test_filter_variants(database):
    by_type = database.filter(program_type="ABLE")
    assert len(by_type) > 0
    assert all(r.program_type == "ABLE" for r in by_type)

    by_assets = database.filter(min_assets=1_000_000_000, max_assets=5_000_000_000)
    assert all(1_000_000_000 <= r.total_assets <= 5_000_000_000 for r in by_assets)

    sample_state = database.filter(program_type="529")[0].state
    combined = database.filter(program_type="529", state=sample_state)
    assert all(r.program_type == "529" and r.state == sample_state for r in combined)


def test_update_record_valid_and_invalid_field(database):
    target = database.all()[0]
    updated = database.update(target.program_id, total_assets=999_999.0)
    assert updated.total_assets == 999_999.0
    assert database.query(target.program_id).total_assets == 999_999.0

    with pytest.raises(ValueError):
        database.update(target.program_id, not_a_real_field=1)


def test_add_and_remove_record(database):
    original_len = len(database)
    new_record = ProgramRecord(
        program_id="P999",
        state="Test State",
        program_type="529",
        program_name="Test State College Savings Plan",
        inception_year=2020,
        program_manager="Test Manager",
        total_assets=1_000_000.0,
        number_of_accounts=100,
        investment_options=[InvestmentOption("Index Fund Option 1", "Index Fund", 5.0)],
        state_admin_fee_bps=5.0,
        fixed_admin_cost_annual=50_000.0,
        history=[HistoricalPoint(2024, 900_000.0, 90), HistoricalPoint(2025, 1_000_000.0, 100)],
    )
    database.add(new_record)
    assert len(database) == original_len + 1
    assert database.query("P999").program_name == "Test State College Savings Plan"

    with pytest.raises(ValueError):
        database.add(new_record)  # duplicate id

    database.remove("P999")
    assert len(database) == original_len
    with pytest.raises(KeyError):
        database.query("P999")


def test_peer_group_and_summary_statistics(database):
    target = database.all()[0]
    peers = database.peer_group(target)
    assert target.program_id not in [p.program_id for p in peers]
    assert all(p.program_type == target.program_type for p in peers)

    stats = database.summary_statistics()
    assert stats["program_count"] == len(database)
    assert stats["total_assets"] == pytest.approx(sum(r.total_assets for r in database))
    assert stats["total_accounts"] == sum(r.number_of_accounts for r in database)
    assert set(stats["by_type"].keys()) == {r.program_type for r in database}


def test_save_and_load_round_trip(database, tmp_path):
    path = os.path.join(tmp_path, "db.json")
    database.save(path)
    loaded = ProgramDatabase.load(path)
    assert len(loaded) == len(database)

    original = database.query(database.all()[0].program_id)
    reloaded = loaded.query(original.program_id)
    assert reloaded.total_assets == original.total_assets
    assert reloaded.program_name == original.program_name
    assert len(reloaded.investment_options) == len(original.investment_options)
    assert len(reloaded.history) == len(original.history)
