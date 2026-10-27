
import sqlite3
from pathlib import Path

root = Path(__file__).parent
db_path = root / "benefits.db"


if not db_path.exists():
    raise FileNotFoundError("Run database.py first.")

conn = sqlite3.connect(db_path)

sql = (root / "sql/queries.sql").read_text()

# This simple runner expects the file to contain
# SELECT queries separated by semicolons.
for query in sql.split(";"):
    # Remove comment-only lines
    lines = [
        line for line in query.splitlines()
        if line.strip() and not line.strip().startswith("--")
    ]
    statement = "\n".join(lines).strip()

    if not statement:
        continue

    cursor = conn.execute(statement)
    print("\nQUERY RESULT:")
    for row in cursor.fetchall():
        print(row)

conn.close()
