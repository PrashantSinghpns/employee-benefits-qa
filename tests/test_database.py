
import sqlite3
import pytest
from pathlib import Path


@pytest.fixture
def db():
    root = Path(__file__).resolve().parents[1]

    # Find SQL files, including your nested layout
    if not (root / "sql/schema.sql").exists():
        root = root / "employee-benefits-qa"

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript(
        (root / "sql/schema.sql").read_text()
    )
    conn.executescript(
        (root / "sql/sample_data.sql").read_text()
    )

    yield conn
    conn.close()


def test_duplicate_prevention(db):
    # Kiran is already enrolled in Medical Plus.
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO enrollments
            (employee_id, plan_id, enrollment_date)
            VALUES (7, 1, '2026-10-15')
        """)


def test_invalid_foreign_key(db):
    # Employee 999 doesn't exist.
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO enrollments
            (employee_id, plan_id, enrollment_date)
            VALUES (999, 1, '2026-10-15')
        """)


def test_invalid_waiting_period(db):
    # Waiting period cannot exceed 365 days.
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            UPDATE benefit_plans
            SET waiting_days = 400
            WHERE plan_id = 1
        """)


def test_transaction_rollback(db):
    before = db.execute(
        "SELECT COUNT(*) FROM enrollments"
    ).fetchone()[0]

    try:
        db.execute("""
            INSERT INTO enrollments
            (employee_id, plan_id, enrollment_date)
            VALUES (1, 2, '2026-10-15')
        """)

        # Deliberate error: nonexistent dependent ID
        db.execute("""
            INSERT INTO enrollment_dependents
            (enrollment_id, dependent_id)
            VALUES (last_insert_rowid(), 999)
        """)

        db.commit()

    except sqlite3.IntegrityError:
        db.rollback()

    after = db.execute(
        "SELECT COUNT(*) FROM enrollments"
    ).fetchone()[0]

    assert before == after


def test_dependent_link_uniqueness(db):
    db.execute("""
        INSERT INTO enrollments
        (employee_id, plan_id, enrollment_date)
        VALUES (1, 1, '2026-10-15')
    """)

    enrollment_id = db.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]

    db.execute("""
        INSERT INTO enrollment_dependents
        VALUES (?, 1)
    """, (enrollment_id,))

    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO enrollment_dependents
            VALUES (?, 1)
        """, (enrollment_id,))
