"""Regression checks for the actual values shown after submitting either form."""
from html.parser import HTMLParser

import pytest


class FormState(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.current_select = None
        self.selected = {}
        self.inputs = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "select":
            self.current_select = attrs.get("name")
        elif tag == "option" and "selected" in attrs:
            self.selected[self.current_select] = attrs.get("value")
        elif tag == "input":
            self.inputs.setdefault(attrs.get("name"), []).append(attrs)

    def handle_endtag(self, tag):
        if tag == "select":
            self.current_select = None


@pytest.mark.parametrize("plan,dependent,message", [
    ("2", None, "Success:"),
    ("1", "2", "Success:"),
    ("1", "1", "belongs to another employee"),
])
def test_enrollment_preserves_submitted_form_values(client, plan, dependent, message):
    # Employee 8 and the non-default date reveal unwanted fallback to Rahul/October 27.
    body = {"employee_id": "8", "plan_id": plan, "enrollment_date": "2026-10-12"}
    if dependent:
        body["dependent_ids"] = dependent
    response = client.post("/", data=body)
    html = response.get_data(as_text=True)
    assert message in html
    form = FormState(html)
    assert form.selected["employee_id"] == "8"
    assert form.selected["plan_id"] == plan
    assert form.inputs["enrollment_date"][0]["value"] == "2026-10-12"
    checked = {item["value"] for item in form.inputs["dependent_ids"] if "checked" in item}
    assert checked == ({dependent} if dependent else set())


@pytest.mark.parametrize("waiting,active", [("60", True), ("60", False), ("366", False)])
def test_configuration_preserves_values_and_checkbox_state(client, waiting, active):
    body = {"plan_id": "2", "eligible_type": "ANY", "waiting_days": waiting,
            "window_start": "2026-10-05", "window_end": "2026-10-30",
            "allow_dependents": "on"}
    if active:
        body["active"] = "on"
    response = client.post("/configure", data=body)
    html = response.get_data(as_text=True)
    assert ("Rejected:" if waiting == "366" else "Configuration saved") in html
    form = FormState(html)
    assert form.selected["plan_id"] == "2"
    assert form.selected["eligible_type"] == "ANY"
    assert form.inputs["waiting_days"][0]["value"] == waiting
    assert form.inputs["window_start"][0]["value"] == "2026-10-05"
    assert form.inputs["window_end"][0]["value"] == "2026-10-30"
    assert ("checked" in form.inputs["active"][0]) is active
    assert "checked" in form.inputs["allow_dependents"][0]


def test_initial_enrollment_date_and_configuration_defaults(client):
    # Preserve the existing first-load defaults while fixing post-submission state.
    form = FormState(client.get("/").get_data(as_text=True))
    assert form.inputs["enrollment_date"][0]["value"] == "2026-10-27"
    configuration = FormState(client.get("/configure").get_data(as_text=True))
    assert configuration.selected["eligible_type"] == "FULL_TIME"
    assert "checked" in configuration.inputs["active"][0]
    assert "checked" not in configuration.inputs["allow_dependents"][0]
