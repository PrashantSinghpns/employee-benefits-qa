import sqlite3
from contextlib import closing

import pytest

from conftest import PROJECT


def test_all_twenty_queries_against_known_baseline(connection):
    queries = [q for q in (PROJECT / "sql/queries.sql").read_text().split(";") if q.strip()]
    assert len(queries) == 20
    # Known fixture counts catch silent changes in joins and eligibility filtering.
    assert [len(connection.execute(q).fetchall()) for q in queries] == [
        7, 6, 2, 2, 8, 1, 9, 1, 2, 0, 3, 3, 0, 7, 2, 0, 0, 0, 0, 0]


def test_initialization_and_safe_reset(tmp_path, database_module):
    path = tmp_path / "benefits.db"
    database_module.initialize(path)
    with pytest.raises(FileExistsError):
        database_module.initialize(path)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("UPDATE employees SET name='Changed locally' WHERE employee_id=1")
        conn.commit()
    database_module.initialize(path, reset=True)
    backups = list(tmp_path.glob("benefits.db.*.bak"))
    assert len(backups) == 1
    with closing(sqlite3.connect(backups[0])) as backup:
        assert backup.execute("SELECT name FROM employees WHERE employee_id=1").fetchone()[0] == "Changed locally"
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("SELECT name FROM employees WHERE employee_id=1").fetchone()[0] == "Rahul"
