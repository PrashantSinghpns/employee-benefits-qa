
import sqlite3
from pathlib import Path
import sys
import pytest

# Locate app.py in your nested project.
root = Path(__file__).resolve().parents[1]
if not (root / "app.py").exists():
    root = root / "employee-benefits-qa"

sys.path.insert(0, str(root))

from app import enroll


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript(
        (root / "sql/schema.sql").read_text()
    )
    conn.executescript(
        (root / "sql/sample_data.sql").read_text()
    )

    # Finish sample-data transaction before testing.
    conn.commit()

    yield conn
    conn.close()


def configure(db, **changes):
    allowed = {
        "waiting_days", "eligible_type",
        "window_start", "window_end",
        "active", "allow_dependents"
    }
    assert changes.keys() <= allowed

    for field, value in changes.items():
        db.execute(
            f"UPDATE benefit_plans SET {field} = ? "
            "WHERE plan_id = 1",
            (value,)
        )
    db.commit()


def test_zero_waiting_days(db):
    configure(db, waiting_days=0)
    result = enroll(db, 2, 1, "2026-10-01")
    assert result.startswith("Success:")


def test_increased_waiting_days(db):
    configure(db, waiting_days=60)
    result = enroll(db, 2, 1, "2026-10-27")
    assert "Waiting period not completed" in result


def test_any_employment_type(db):
    configure(db, eligible_type="ANY")
    result = enroll(db, 3, 1, "2026-10-10")
    assert result.startswith("Success:")


def test_full_time_only(db):
    configure(db, eligible_type="FULL_TIME")
    result = enroll(db, 3, 1, "2026-10-10")
    assert "Employment type not eligible" in result


def test_move_start_date(db):
    configure(db, window_start="2026-10-15")
    result = enroll(db, 8, 1, "2026-10-10")
    assert "Outside enrollment window" in result


def test_move_end_date(db):
    configure(db, window_end="2026-10-05")
    result = enroll(db, 8, 1, "2026-10-10")
    assert "Outside enrollment window" in result


def test_deactivate_plan(db):
    configure(db, active=0)
    result = enroll(db, 8, 1, "2026-10-10")
    assert "Plan is inactive" in result


def test_disable_dependents(db):
    configure(db, allow_dependents=0)
    result = enroll(
        db, 8, 1, "2026-10-10", ["2"]
    )
    assert "Plan does not allow dependents" in result


def test_configuration_constraint(db):
    with pytest.raises(sqlite3.IntegrityError):
        configure(db, waiting_days=400)
