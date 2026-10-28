"""Protect the asset paths and saved-plan loading that caused the damaged screen."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys

import pytest


class Fields(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.inputs = {}
        self.selected = {}
        self.current = None
        self.feed(text)

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        if tag == "select":
            self.current = attrs.get("name")
        elif tag == "option" and "selected" in attrs:
            self.selected[self.current] = attrs.get("value")
        elif tag == "input":
            self.inputs[attrs.get("name")] = attrs


def test_styles_and_script_are_served_from_the_canonical_app(client):
    css = client.get("/static/style.css")
    script = client.get("/static/app.js")
    assert css.status_code == script.status_code == 200
    assert css.mimetype == "text/css"
    assert b".enrollment-grid" in css.data
    assert b"application/json" in script.data
    assert b"/static/style.css?v=3" in client.get("/").data


def test_records_endpoint_returns_json_instead_of_an_html_error(client):
    response = client.get("/api/data")
    assert response.status_code == 200 and response.is_json
    assert len(response.json["employees"]) == 8
    assert response.json["plans"][1]["eligible_type"] == "ANY"
    assert len(response.json["enrollments"]) == 1


def test_missing_database_has_a_useful_page_and_json_error(application, client, tmp_path):
    application.config["DATABASE"] = tmp_path / "missing.sqlite"
    page = client.get("/")
    api = client.get("/api/data")
    assert page.status_code == api.status_code == 503
    assert api.is_json and "Sample data" in api.json["error"]
    assert b"init-db" in page.data


@pytest.mark.parametrize("plan_id,eligible,waiting,active", [("2", "ANY", "0", True), ("3", "FULL_TIME", "0", False)])
def test_chosen_plan_loads_persisted_settings(client, plan_id, eligible, waiting, active):
    form = Fields(client.get("/configure", query_string={"plan_id": plan_id}).get_data(as_text=True))
    assert form.selected["plan_id"] == plan_id
    assert form.selected["eligible_type"] == eligible
    assert form.inputs["waiting_days"]["value"] == waiting
    assert ("checked" in form.inputs["active"]) == active
    assert "checked" not in form.inputs["allow_dependents"]


def test_reopening_configuration_uses_saved_values_not_initial_defaults(client):
    body = {"plan_id": "1", "eligible_type": "ANY", "waiting_days": "60",
            "window_start": "2026-10-05", "window_end": "2026-10-30", "allow_dependents": "on"}
    assert b"Configuration saved" in client.post("/configure", data=body).data
    form = Fields(client.get("/configure?plan_id=1").get_data(as_text=True))
    assert form.selected["eligible_type"] == "ANY"
    assert form.inputs["waiting_days"]["value"] == "60"
    assert form.inputs["window_start"]["value"] == "2026-10-05"
    assert "checked" not in form.inputs["active"]
    assert "checked" in form.inputs["allow_dependents"]


def test_root_launcher_exposes_the_same_routes():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-m", "flask", "--app", "app", "routes"], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "/api/data" in result.stdout and "/configure" in result.stdout


def test_initialization_command_uses_the_canonical_schema(application, tmp_path):
    application.config["DATABASE"] = tmp_path / "new-demo.db"
    result = application.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0, result.output
    with application.test_client() as client:
        assert len(client.get("/api/data").json["employees"]) == 8
