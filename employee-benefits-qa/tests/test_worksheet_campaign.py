"""Execute worksheet scenarios through Flask requests and inspect persisted SQLite data.

These are automated request/database checks, not human or agent-driven browser executions.
"""
import html
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

CASES = [f"TC{number:02}" for number in range(1, 31)]


def snapshot(connection):
    return {
        "enrollments": [dict(row) for row in connection.execute(
            "SELECT * FROM enrollments ORDER BY enrollment_id")],
        "dependent_links": [dict(row) for row in connection.execute(
            "SELECT * FROM enrollment_dependents ORDER BY enrollment_id,dependent_id")],
    }


@pytest.mark.parametrize("case_id", CASES, ids=CASES)
def test_worksheet_scenario(case_id, client, connection):
    record = {
        "test_id": case_id,
        "tested_commit": os.environ.get("GITHUB_SHA", "local-working-tree"),
        "executed_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(),
        "method": "Automated Flask test-client request + SQLite verification",
        "environment": {"python": platform.python_version(),
                        "flask": importlib.metadata.version("Flask"),
                        "sqlite": sqlite3.sqlite_version, "platform": platform.system()},
        "initial_database": snapshot(connection),
        "requests": [], "assertions": [], "status": "Fail",
    }

    def check(description, actual, expected):
        passed = actual == expected
        record["assertions"].append(
            {"description": description, "actual": actual, "expected": expected, "passed": passed})
        assert passed, f"{case_id}: {description}: {actual!r} != {expected!r}"

    def post(path, body):
        response = client.post(path, data=body)
        match = re.search(r"(Success:|Rejected:)[^<]+", response.get_data(as_text=True))
        message = html.unescape(match.group(0).strip()) if match else "No result message"
        record["requests"].append({"path": path, "form": body,
                                   "http_status": response.status_code, "message": message})
        check("Request handled without server error", response.status_code, 200)
        return message

    def enroll(body, message_fragment, accepted=False, links=0):
        before = snapshot(connection)
        message = post("/", body)
        check("Expected response message", message_fragment in message, True)
        after = snapshot(connection)
        check("Enrollment count", len(after["enrollments"]), 2 if accepted else 1)
        check("Dependent-link count", len(after["dependent_links"]), links)
        if not accepted:
            check("Rejected submission changes no enrollment/link rows", after, before)
        else:
            row = after["enrollments"][-1]
            check("Saved employee", row["employee_id"], int(body["employee_id"]))
            check("Saved plan", row["plan_id"], int(body["plan_id"]))
            check("Saved scenario date", row["enrollment_date"], body["enrollment_date"])
            if links:
                check("Saved dependent ownership link",
                      after["dependent_links"][0]["dependent_id"],
                      int(body["dependent_ids"]))
        return message

    def configure(**changes):
        body = {"plan_id": "1", "eligible_type": "FULL_TIME", "waiting_days": "30",
                "window_start": "2026-10-01", "window_end": "2026-10-31",
                "active": "on", "allow_dependents": "on"}
        for field, value in changes.items():
            if value is False:
                body.pop(field, None)
            else:
                body[field] = str(value)
        check("Configuration accepted", "Configuration saved" in post("/configure", body), True)
        plan = dict(connection.execute("SELECT * FROM benefit_plans WHERE plan_id=1").fetchone())
        for field in ("eligible_type", "waiting_days", "window_start", "window_end",
                      "active", "allow_dependents"):
            expected = int(field in body) if field in ("active", "allow_dependents") else body[field]
            if field == "waiting_days":
                expected = int(expected)
            check(f"Persisted configuration {field}", plan[field], expected)

    body = {"employee_id": "1", "plan_id": "1", "enrollment_date": "2026-10-10"}
    fault_installed = False
    try:
        if case_id == "TC01":
            enroll({**body, "plan_id": "2"}, "Success:", accepted=True)
        elif case_id == "TC02":
            enroll({**body, "dependent_ids": "1"}, "Success:", accepted=True, links=1)
        elif case_id == "TC03":
            enroll({**body, "employee_id": "7", "plan_id": "2"}, "Success:", accepted=True)
            check("Employee has two distinct plans", connection.execute(
                "SELECT COUNT(DISTINCT plan_id) FROM enrollments WHERE employee_id=7").fetchone()[0], 2)
        elif case_id == "TC04":
            enroll({**body, "employee_id": "4"}, "Employee is inactive")
        elif case_id == "TC05":
            enroll({**body, "plan_id": "3"}, "Plan is inactive")
        elif case_id == "TC06":
            enroll({**body, "employee_id": "3"}, "Employment type not eligible")
        elif case_id == "TC07":
            enroll({**body, "employee_id": "5", "plan_id": "2",
                    "enrollment_date": "2026-10-27"}, "Waiting period not completed")
        elif case_id in ("TC08", "TC09", "TC10"):
            day = {"TC08": "26", "TC09": "27", "TC10": "28"}[case_id]
            accepted = case_id != "TC08"
            enroll({**body, "employee_id": "2", "enrollment_date": "2026-10-" + day},
                   "Success:" if accepted else "Waiting period not completed", accepted=accepted)
        elif case_id in ("TC11", "TC12", "TC13", "TC14"):
            scenario_date = {"TC11": "2026-09-30", "TC12": "2026-10-01",
                             "TC13": "2026-10-31", "TC14": "2026-11-01"}[case_id]
            accepted = case_id in ("TC12", "TC13")
            employee = "1" if case_id == "TC14" else "8"
            enroll({**body, "employee_id": employee, "enrollment_date": scenario_date},
                   "Success:" if accepted else "Outside enrollment window", accepted=accepted)
        elif case_id == "TC15":
            enroll({**body, "employee_id": "7"}, "Duplicate enrollment")
        elif case_id == "TC16":
            # Back-to-back repeat requests exercise duplicate handling, not simultaneous load.
            record["scope_note"] = "Two back-to-back submissions; no concurrency/load claim."
            check("First repeat request succeeds", "Success:" in post("/", body), True)
            first_state = snapshot(connection)
            check("Second repeat rejected", "Duplicate enrollment" in post("/", body), True)
            check("Only one new enrollment", len(first_state["enrollments"]), 2)
            check("Repeat does not change records", snapshot(connection), first_state)
        elif case_id == "TC17":
            missing = dict(body)
            del missing["employee_id"]
            enroll(missing, "Invalid input")
        elif case_id == "TC18":
            enroll({**body, "employee_id": "999"}, "not found")
        elif case_id == "TC19":
            enroll({**body, "enrollment_date": "2026-02-30"}, "Invalid input")
        elif case_id == "TC20":
            enroll({**body, "employee_id": "8", "dependent_ids": "1"},
                   "belongs to another employee")
        elif case_id == "TC21":
            enroll({**body, "dependent_ids": ["1", "01"]}, "Duplicate dependent IDs")
        elif case_id == "TC22":
            # This is deliberate fault injection, not evidence of a product defect.
            record["scope_note"] = "Controlled SQLite trigger failure after the enrollment insert."
            connection.execute("""CREATE TRIGGER reject_campaign_dependent
                BEFORE INSERT ON enrollment_dependents
                BEGIN SELECT RAISE(ABORT, 'controlled worksheet failure'); END""")
            connection.commit()
            fault_installed = True
            enroll({**body, "dependent_ids": "1"}, "No changes saved")
        elif case_id == "TC23":
            configure(waiting_days="0")
            enroll({**body, "employee_id": "2", "enrollment_date": "2026-10-01"},
                   "Success:", accepted=True)
        elif case_id == "TC24":
            configure(waiting_days="60")
            enroll({**body, "employee_id": "2", "enrollment_date": "2026-10-27"},
                   "Waiting period not completed")
        elif case_id == "TC25":
            configure(eligible_type="ANY")
            enroll({**body, "employee_id": "3"}, "Success:", accepted=True)
        elif case_id == "TC26":
            configure(eligible_type="ANY")
            configure(eligible_type="FULL_TIME")
            enroll({**body, "employee_id": "3"}, "Employment type not eligible")
        elif case_id == "TC27":
            configure(window_start="2026-10-15")
            enroll({**body, "employee_id": "8"}, "Outside enrollment window")
        elif case_id == "TC28":
            configure(window_end="2026-10-05")
            enroll({**body, "employee_id": "8"}, "Outside enrollment window")
        elif case_id == "TC29":
            configure(active=False)
            enroll({**body, "employee_id": "8"}, "Plan is inactive")
        elif case_id == "TC30":
            configure(allow_dependents=False)
            enroll({**body, "employee_id": "8", "dependent_ids": "2"},
                   "Plan does not allow dependents")
        record["status"] = "Pass"
    except Exception as error:
        record["exception"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        if fault_installed:
            connection.execute("DROP TRIGGER IF EXISTS reject_campaign_dependent")
            connection.commit()
        record["final_database"] = snapshot(connection)
        destination = Path("artifacts/campaign")
        destination.mkdir(parents=True, exist_ok=True)
        (destination / f"{case_id}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        # Console JSON allows independent retrieval through GitHub's job-log connector.
        print("CAMPAIGN_RESULT " + json.dumps(record, separators=(",", ":")))
