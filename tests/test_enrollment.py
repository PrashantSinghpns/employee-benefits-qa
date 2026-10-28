
import sqlite3
import pytest
from pathlib import Path

import sys
from pathlib import Path

project_dir = Path(__file__).resolve().parents[1] / "employee-benefits-qa"
sys.path.insert(0, str(project_dir))

from app import enroll


@pytest.fixture
def db():
    # Create a separate database for every test.
    # Your real benefits.db remains untouched.
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    root = project_dir

    schema = (root / "sql/schema.sql").read_text()
    sample = (root / "sql/sample_data.sql").read_text()

    conn.executescript(schema)
    conn.executescript(sample)

    yield conn
    conn.close()


def count_enrollments(db):
    return db.execute(
        "SELECT COUNT(*) FROM enrollments"
    ).fetchone()[0]


# TC01: Valid enrollment
def test_valid_enrollment(db):
    result = enroll(db, 1, 2, "2026-10-10")
    assert result.startswith("Success:")
    assert count_enrollments(db) == 2


# TC04: Inactive employee
def test_inactive_employee(db):
    result = enroll(db, 4, 1, "2026-10-10")
    assert "Employee is inactive" in result
    assert count_enrollments(db) == 1


# TC05: Inactive plan
def test_inactive_plan(db):
    result = enroll(db, 1, 3, "2026-10-10")
    assert "Plan is inactive" in result
    assert count_enrollments(db) == 1


# TC06: Employment type mismatch
def test_wrong_employment_type(db):
    result = enroll(db, 3, 1, "2026-10-10")
    assert "Employment type not eligible" in result


# TC08: Waiting period incomplete
def test_waiting_period(db):
    result = enroll(db, 2, 1, "2026-10-26")
    assert "Waiting period not completed" in result


# TC09: Exact waiting period boundary
def test_waiting_period_boundary(db):
    result = enroll(db, 2, 1, "2026-10-27")
    assert result.startswith("Success:")


# TC11: Before enrollment window

def test_before_window(db):
    # Anjali completed her waiting period
    # before the enrollment window begins.
    result = enroll(db, 8, 1, "2026-09-30")

    assert "Outside enrollment window" in result
    assert count_enrollments(db) == 1



# TC14: After enrollment window
def test_after_window(db):
    result = enroll(db, 1, 1, "2026-11-01")
    assert "Outside enrollment window" in result


# TC15: Duplicate enrollment
def test_duplicate(db):
    result = enroll(db, 7, 1, "2026-10-10")
    assert "Duplicate enrollment" in result
    assert count_enrollments(db) == 1


# TC20: Incorrect dependent ownership
def test_wrong_dependent(db):
    result = enroll(
        db, 8, 1, "2026-10-10", ["1"]
    )
    assert "belongs to another employee" in result
    assert count_enrollments(db) == 1


# TC02: Valid dependent enrollment
def test_valid_dependent(db):
    result = enroll(
        db, 1, 1, "2026-10-10", ["1"]
    )
    assert result.startswith("Success:")

    links = db.execute(
        "SELECT COUNT(*) FROM enrollment_dependents"
    ).fetchone()[0]

    assert links == 1


# TC19: Invalid date
def test_invalid_date(db):
    result = enroll(db, 1, 2, "2026-02-30")
    assert "Invalid input" in result
    assert count_enrollments(db) == 1
