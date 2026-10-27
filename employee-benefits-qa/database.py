"""Initialize fictional data; explicitly back up existing data before a reset."""
import argparse
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent


def initialize(path, reset=False):
    path = Path(path)
    if path.exists():
        if not reset:
            raise FileExistsError("Database exists. Use --reset to back it up and restore sample data.")
        # SQLite backup includes committed data when journaling is enabled.
        backup = path.with_name(path.name + datetime.now().strftime(".%Y%m%d-%H%M%S-%f.bak"))
        with closing(sqlite3.connect(path)) as source, closing(sqlite3.connect(backup)) as target:
            source.backup(target)
        path.unlink()
        print(f"Backup saved: {backup}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript((ROOT / "sql/schema.sql").read_text(encoding="utf-8"))
        conn.executescript((ROOT / "sql/sample_data.sql").read_text(encoding="utf-8"))
    print(f"Sample database ready: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "benefits.db")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    try:
        initialize(args.database, args.reset)
    except FileExistsError as error:
        parser.exit(1, str(error) + "\n")
