from flask import Flask, render_template_string, request
import sqlite3
import re
from contextlib import closing
from pathlib import Path
from datetime import date, timedelta

app = Flask(__name__)
DB = Path(__file__).parent / "benefits.db"


def get_db():
    conn = sqlite3.connect(app.config.get("DATABASE", DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def parse_id(value):
    # Reject oversized values before SQLite converts them to signed 64-bit integers.
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Invalid ID")
    text = str(value)
    if not re.fullmatch(r"[0-9]{1,19}", text):
        raise ValueError("Invalid ID")
    number = int(text)
    if not 1 <= number <= 9223372036854775807:
        raise ValueError("Invalid ID")
    return number


def parse_date(value):
    # A single format keeps scenario inputs and database comparisons consistent.
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Date must use YYYY-MM-DD")
    return date.fromisoformat(value)


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Employee Benefits QA</title>
    <style>
        body {font-family: Arial; max-width: 750px;
              margin: 40px auto; padding: 20px;}
        h1 {color: #2563eb;}
        form {background: #f1f5f9; padding: 25px;
              border-radius: 12px;}
        label {display: block; margin-top: 15px;}
        select, input, button {padding: 10px; width: 100%;
              box-sizing: border-box; margin-top: 5px;}
        button {background: #2563eb; color: white;
                border: 0; margin-top: 20px; cursor: pointer;}
        .result {padding: 15px; margin-top: 20px;
                 border-radius: 8px; background: #e2e8f0;}
    </style>
</head>
<body>
    <h1>Employee Benefits Administration</h1>
    <p>Enrollment & Eligibility Testing</p>
    <p><a href="/configure">Configure benefit plans</a></p>
    <p>Use fictional records and an explicit scenario date for repeatable testing.</p>

    <form method="POST">
        <label>Employee</label>
        <select name="employee_id" required>
            {% for e in employees %}
            <option value="{{ e['employee_id'] }}">
                {{ e['name'] }} — {{ e['employment_type'] }}
            </option>
            {% endfor %}
        </select>

        <label>Benefit Plan</label>
        <select name="plan_id" required>
            {% for p in plans %}
            <option value="{{ p['plan_id'] }}">
                {{ p['name'] }}
            </option>
            {% endfor %}
        </select>

        <label>Enrollment Date</label>
        <input type="date" name="enrollment_date"
               value="2026-10-27" required>
               
<label>Dependents (optional)</label>

{% for d in dependents %}
<label>
    <input type="checkbox"
           name="dependent_ids"
           value="{{ d['dependent_id'] }}"
           style="width:auto">
    {{ d['name'] }} — Employee ID {{ d['employee_id'] }}
</label>
{% endfor %}

        <button type="submit">Check & Enroll</button>
    </form>

    {% if message %}
    <div class="result">{{ message }}</div>
    {% endif %}
    <h2>Current records</h2>
    {% for title, rows in [('Employees', employees), ('Plans', plans),
                            ('Dependents', dependents), ('Enrollments', enrollments)] %}
    <details><summary>{{ title }} ({{ rows|length }})</summary>
    {% for row in rows %}<p>{{ dict(row) }}</p>{% else %}<p>No records.</p>{% endfor %}
    </details>
    {% endfor %}
</body>
</html>
"""


def enroll(conn, employee_id, plan_id, enrollment_date, dependent_ids=None):
    # Validate submitted IDs
    try:
        employee_id = parse_id(employee_id)
        plan_id = parse_id(plan_id)
        submitted = parse_date(enrollment_date)
    except (ValueError, TypeError):
        return "Rejected: Invalid input."

    employee = conn.execute(
        "SELECT * FROM employees WHERE employee_id = ?",
        (employee_id,)
    ).fetchone()

    plan = conn.execute(
        "SELECT * FROM benefit_plans WHERE plan_id = ?",
        (plan_id,)
    ).fetchone()

    if employee is None or plan is None:
        return "Rejected: Employee or plan not found."

    if not employee["active"]:
        return "Rejected: Employee is inactive."

    if not plan["active"]:
        return "Rejected: Plan is inactive."

    if (plan["eligible_type"] != "ANY" and
            employee["employment_type"] != plan["eligible_type"]):
        return "Rejected: Employment type not eligible."

    hire_date = date.fromisoformat(employee["hire_date"])
    eligible_date = hire_date + timedelta(days=plan["waiting_days"])

    if submitted < eligible_date:
        return "Rejected: Waiting period not completed."

    start = date.fromisoformat(plan["window_start"])
    end = date.fromisoformat(plan["window_end"])

    if not start <= submitted <= end:
        return "Rejected: Outside enrollment window."

    existing = conn.execute(
        """SELECT 1 FROM enrollments
           WHERE employee_id = ? AND plan_id = ?""",
        (employee_id, plan_id)
    ).fetchone()

    if existing:
        return "Rejected: Duplicate enrollment."
    
    
    if dependent_ids is None:
        dependent_ids = []
    if not isinstance(dependent_ids, (list, tuple)):
        return "Rejected: Invalid dependent IDs."
    try:
        # Normalize first, so '1' and '01' identify the same dependent.
        dependent_ids = [parse_id(value) for value in dependent_ids]
    except ValueError:
        return "Rejected: Invalid dependent ID."

    if len(dependent_ids) != len(set(dependent_ids)):
        return "Rejected: Duplicate dependent IDs."

    if dependent_ids and not plan["allow_dependents"]:
        return "Rejected: Plan does not allow dependents."

    for dependent_id in dependent_ids:
        try:
            dependent_id = int(dependent_id)
        except (ValueError, TypeError):
            return "Rejected: Invalid dependent ID."

        dependent = conn.execute(
            """SELECT * FROM dependents
               WHERE dependent_id = ?""",
            (dependent_id,)
        ).fetchone()

        if dependent is None:
            return "Rejected: Dependent not found."

        if dependent["employee_id"] != employee_id:
            return "Rejected: Dependent belongs to another employee."


    try:
        cursor = conn.execute(
            """INSERT INTO enrollments
               (employee_id, plan_id, enrollment_date)
               VALUES (?, ?, ?)""",
            (employee_id, plan_id, submitted.isoformat())
        )

        enrollment_id = cursor.lastrowid

        for dependent_id in dependent_ids:
            conn.execute(
                """INSERT INTO enrollment_dependents
                   (enrollment_id, dependent_id)
                   VALUES (?, ?)""",
                (enrollment_id, int(dependent_id))
            )

        conn.commit()
        return "Success: Enrollment and dependents saved!"

    except sqlite3.IntegrityError:
        conn.rollback()
        return "Rejected: Enrollment failed. No changes saved."



@app.route("/", methods=["GET", "POST"])
def home():
    message = None

    # SQLite's transaction context does not close its connection; closing does.
    with closing(get_db()) as conn:
        if request.method == "POST":
            message = enroll(
                conn,
                request.form.get("employee_id"),
                request.form.get("plan_id"),
                request.form.get("enrollment_date"),
                request.form.getlist("dependent_ids")
            )

        employees = conn.execute(
            "SELECT * FROM employees"
        ).fetchall()

        plans = conn.execute(
            "SELECT * FROM benefit_plans"
        ).fetchall()
        
        
        dependents = conn.execute(
            "SELECT * FROM dependents"
        ).fetchall()
        enrollments = conn.execute("SELECT * FROM enrollments ORDER BY enrollment_id").fetchall()


    return render_template_string(
        HTML, employees=employees,
        plans=plans, message=message, dependents=dependents, enrollments=enrollments, dict=dict
    )


CONFIG_HTML = """
<h1>Benefit Plan Configuration</h1>
<a href="/">Back to Enrollment</a>

<form method="POST">
    <p>Select Plan:
        <select name="plan_id" required>
        {% for p in plans %}
            <option value="{{ p['plan_id'] }}">
                {{ p['name'] }}
            </option>
        {% endfor %}
        </select>
    </p>

    <p>Eligible Employment Type:
        <select name="eligible_type">
            <option>FULL_TIME</option>
            <option>PART_TIME</option>
            <option>CONTRACT</option>
            <option>ANY</option>
        </select>
    </p>

    <p>Waiting Period (0–365 days):
        <input type="number" name="waiting_days"
               min="0" max="365" required>
    </p>

    <p>Enrollment Start:
        <input type="date" name="window_start" required>
    </p>

    <p>Enrollment End:
        <input type="date" name="window_end" required>
    </p>

    <p>Active:
        <input type="checkbox" name="active" checked>
    </p>

    <p>Allow Dependents:
        <input type="checkbox" name="allow_dependents">
    </p>

    <button type="submit">Save Configuration</button>
</form>

<p>{{ message or "" }}</p>
"""


@app.route("/configure", methods=["GET", "POST"])
def configure():
    message = None

    with closing(get_db()) as conn:
        if request.method == "POST":
            try:
                plan_id = parse_id(request.form["plan_id"])
                eligible = request.form["eligible_type"]
                waiting = int(request.form["waiting_days"])

                start = parse_date(
                    request.form["window_start"]
                )
                end = parse_date(
                    request.form["window_end"]
                )

                if eligible not in (
                    "FULL_TIME", "PART_TIME",
                    "CONTRACT", "ANY"
                ):
                    raise ValueError("Invalid employment type")

                if not 0 <= waiting <= 365:
                    raise ValueError("Waiting days must be 0–365")

                if end < start:
                    raise ValueError("End date precedes start date")

                active = int("active" in request.form)
                dependents = int(
                    "allow_dependents" in request.form
                )

                cursor = conn.execute("""
                    UPDATE benefit_plans
                    SET eligible_type = ?,
                        waiting_days = ?,
                        window_start = ?,
                        window_end = ?,
                        active = ?,
                        allow_dependents = ?
                    WHERE plan_id = ?
                """, (
                    eligible, waiting,
                    start.isoformat(), end.isoformat(),
                    active, dependents, plan_id
                ))

                if cursor.rowcount == 0:
                    conn.rollback()
                    message = "Rejected: Plan not found."
                else:
                    conn.commit()
                    message = "Success: Configuration saved!"

            except (ValueError, KeyError) as error:
                message = f"Rejected: {error}"

        plans = conn.execute(
            "SELECT * FROM benefit_plans"
        ).fetchall()

    return render_template_string(
        CONFIG_HTML, plans=plans, message=message
    )

if __name__ == "__main__":
    app.run(debug=True)
