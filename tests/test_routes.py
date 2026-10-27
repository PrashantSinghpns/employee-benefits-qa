import sqlite3

import pytest

from app import enroll


def enrollment(**changes):
    return {"employee_id": "1", "plan_id": "1", "enrollment_date": "2026-10-10", **changes}


def configuration(**changes):
    return {"plan_id": "1", "eligible_type": "FULL_TIME", "waiting_days": "30",
            "window_start": "2026-10-01", "window_end": "2026-10-31",
            "active": "on", "allow_dependents": "on", **changes}


def count(connection):
    return connection.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]


def test_records_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Current records" in response.data
    assert b"Kiran" in response.data
    assert b"Plan configuration" in response.data


def test_configuration_page(client):
    response = client.get("/configure")
    assert response.status_code == 200
    assert b"Benefit Plan Configuration" in response.data


def test_enrollment_form_saves_dependent(client, connection):
    response = client.post("/", data=enrollment(dependent_ids="1"))
    assert b"Success:" in response.data
    assert count(connection) == 2
    assert connection.execute("SELECT COUNT(*) FROM enrollment_dependents").fetchone()[0] == 1


@pytest.mark.parametrize("field,value", [
    ("employee_id", "9" * 30), ("plan_id", "9223372036854775808"),
    ("employee_id", "0"), ("employee_id", "-1"), ("employee_id", "1.5"),
    ("employee_id", ""), ("employee_id", "not-an-id"),
    ("enrollment_date", "2026-02-30"), ("enrollment_date", "20261010"),
])
def test_invalid_enrollment_form_does_not_write(client, connection, field, value):
    response = client.post("/", data=enrollment(**{field: value}))
    assert response.status_code == 200
    assert b"Rejected: Invalid input" in response.data
    assert count(connection) == 1


def test_missing_employee_form_field(client, connection):
    body = enrollment()
    del body["employee_id"]
    response = client.post("/", data=body)
    assert b"Rejected: Invalid input" in response.data
    assert count(connection) == 1


@pytest.mark.parametrize("changes,message", [
    ({"employee_id": "999"}, b"not found"),
    ({"employee_id": "4"}, b"Employee is inactive"),
    ({"plan_id": "3"}, b"Plan is inactive"),
    ({"employee_id": "3"}, b"Employment type not eligible"),
    ({"dependent_ids": "2"}, b"belongs to another employee"),
    ({"dependent_ids": "999"}, b"Dependent not found"),
    ({"dependent_ids": "9" * 30}, b"Invalid dependent ID"),
    ({"dependent_ids": ["1", "01"]}, b"Duplicate dependent IDs"),
])
def test_rejected_enrollment_form(client, connection, changes, message):
    response = client.post("/", data=enrollment(**changes))
    assert message in response.data
    assert count(connection) == 1


def test_repeated_submission_only_saves_once(client, connection):
    assert b"Success:" in client.post("/", data=enrollment()).data
    assert b"Duplicate enrollment" in client.post("/", data=enrollment()).data
    assert count(connection) == 2


@pytest.mark.parametrize("scenario_date", ["2026-10-01", "2026-10-31"])
def test_window_boundaries_through_form(client, connection, scenario_date):
    response = client.post("/", data=enrollment(employee_id="8", enrollment_date=scenario_date))
    assert b"Success:" in response.data
    assert count(connection) == 2


def test_valid_configuration_affects_next_submission(client, connection):
    response = client.post("/configure", data=configuration(eligible_type="ANY", waiting_days="0"))
    assert b"Configuration saved" in response.data
    plan = connection.execute("SELECT * FROM benefit_plans WHERE plan_id=1").fetchone()
    assert (plan["eligible_type"], plan["waiting_days"]) == ("ANY", 0)
    assert b"Success:" in client.post("/", data=enrollment(employee_id="3")).data


@pytest.mark.parametrize("changes,message", [
    ({"waiting_days": "-1"}, b"Waiting days"),
    ({"waiting_days": "366"}, b"Waiting days"),
    ({"waiting_days": "1.5"}, b"Rejected:"),
    ({"window_start": "2026-11-01"}, b"End date precedes"),
    ({"window_end": "2026-02-30"}, b"Rejected:"),
    ({"eligible_type": "INVALID"}, b"Invalid employment type"),
    ({"plan_id": "999"}, b"Plan not found"),
    ({"plan_id": "9" * 30}, b"Invalid ID"),
])
def test_invalid_configuration_preserves_plan(client, connection, changes, message):
    before = tuple(connection.execute("SELECT * FROM benefit_plans WHERE plan_id=1").fetchone())
    response = client.post("/configure", data=configuration(**changes))
    assert response.status_code == 200
    assert message in response.data
    assert tuple(connection.execute("SELECT * FROM benefit_plans WHERE plan_id=1").fetchone()) == before


def test_missing_configuration_field(client, connection):
    body = configuration()
    del body["waiting_days"]
    response = client.post("/configure", data=body)
    assert b"Rejected:" in response.data
    assert connection.execute("SELECT waiting_days FROM benefit_plans WHERE plan_id=1").fetchone()[0] == 30


def test_disabled_checkboxes_persist(client, connection):
    body = configuration()
    del body["active"], body["allow_dependents"]
    assert b"Configuration saved" in client.post("/configure", data=body).data
    row = connection.execute("SELECT active,allow_dependents FROM benefit_plans WHERE plan_id=1").fetchone()
    assert tuple(row) == (0, 0)
    assert b"Plan is inactive" in client.post("/", data=enrollment()).data


def test_configuration_preserves_existing_enrollments(client, connection):
    assert b"Configuration saved" in client.post("/configure", data=configuration(waiting_days="365")).data
    assert count(connection) == 1


def test_zero_waiting_future_hire_rejected(client, connection):
    assert b"Configuration saved" in client.post("/configure", data=configuration(waiting_days="0")).data
    response = client.post("/", data=enrollment(employee_id="5", enrollment_date="2026-10-27"))
    assert b"Waiting period not completed" in response.data
    assert count(connection) == 1


def test_application_rolls_back_on_dependent_insert_failure(client, connection):
    # Inject a failure after the enrollment insert to exercise the application's rollback.
    connection.execute("""CREATE TRIGGER reject_dependent BEFORE INSERT ON enrollment_dependents
                       BEGIN SELECT RAISE(ABORT, 'controlled test failure'); END""")
    connection.commit()
    response = client.post("/", data=enrollment(dependent_ids="1"))
    assert b"No changes saved" in response.data
    assert count(connection) == 1
    assert connection.execute("SELECT COUNT(*) FROM enrollment_dependents").fetchone()[0] == 0


@pytest.mark.parametrize("value", [True, 1.5, "9223372036854775808"])
def test_direct_function_rejects_non_integer_or_oversized_id(connection, value):
    assert "Invalid input" in enroll(connection, value, 1, "2026-10-10")
    assert count(connection) == 1

