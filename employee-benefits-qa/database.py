
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
DB = ROOT / "benefits.db"

with sqlite3.connect(DB) as conn:
    conn.execute("PRAGMA foreign_keys = ON")

    schema = (ROOT / "sql/schema.sql").read_text()
    sample = (ROOT / "sql/sample_data.sql").read_text()

    conn.executescript(schema)
    conn.executescript(sample)

    rows = conn.execute(
        "SELECT employee_id, name FROM employees"
    ).fetchall()

    print("Employees:", rows)
    print("Database created successfully!")
