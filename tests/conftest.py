"""Shared fixtures isolate Flask requests from the user's working database."""
import importlib.util
import sqlite3
from contextlib import closing
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1] / "employee-benefits-qa"
sys.path.insert(0, str(PROJECT))
from app import app


@pytest.fixture
def application(tmp_path):
    path = tmp_path / "benefits.db"
    with closing(sqlite3.connect(path)) as conn:
        conn.executescript((PROJECT / "sql/schema.sql").read_text())
        conn.executescript((PROJECT / "sql/sample_data.sql").read_text())
    original = app.config.copy()
    app.config.update(TESTING=True, DATABASE=path)
    yield app
    app.config.clear()
    app.config.update(original)


@pytest.fixture
def client(application):
    return application.test_client()


@pytest.fixture
def connection(application):
    with closing(sqlite3.connect(application.config["DATABASE"])) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn


@pytest.fixture
def database_module():
    # Loading by filename avoids executing the command-line entry point.
    spec = importlib.util.spec_from_file_location("benefits_database", PROJECT / "database.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
