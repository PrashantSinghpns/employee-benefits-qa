from flask import Flask, render_template, request, jsonify
import sqlite3
import re
from contextlib import closing
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parent
# Absolute asset paths make both supported launch commands serve the same UI.
app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))
DB = ROOT / "benefits.db"


def get_db():
    database = Path(app.config.get("DATABASE", DB))
    if not database.exists():
        raise sqlite3.OperationalError("Sample database is not initialized.")
    conn = sqlite3.connect(database)
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


    records = {"employees": [dict(row) for row in employees], "plans": [dict(row) for row in plans],
               "dependents": [dict(row) for row in dependents], "enrollments": [dict(row) for row in enrollments]}
    return render_template(
        "index.html", employees=employees, plans=plans, message=message, dependents=dependents,
        enrollments=enrollments, record_data=records, active_page="enrollment"
    )


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

    plan_records = [dict(row) for row in plans]
    requested_id = request.form.get("plan_id") if request.method == "POST" else request.args.get("plan_id")
    selected = next((row for row in plan_records if str(row["plan_id"]) == str(requested_id)), plan_records[0] if plan_records else None)
    # On GET show persisted settings; on POST preserve submitted values, including invalid ones.
    values = dict(selected or {})
    if request.method == "POST":
        for field in ("plan_id", "eligible_type", "waiting_days", "window_start", "window_end"):
            values[field] = request.form.get(field, "")
        values["active"] = "active" in request.form
        values["allow_dependents"] = "allow_dependents" in request.form
    return render_template(
        "configure.html", plans=plan_records, values=values, message=message,
        plan_data=plan_records, active_page="configuration"
    )

@app.get("/api/data")
def record_data():
    # Return actual JSON for the records panel, using the canonical database schema.
    with closing(get_db()) as conn:
        tables = {"employees": ("employees", "employee_id"), "plans": ("benefit_plans", "plan_id"),
                  "dependents": ("dependents", "dependent_id"), "enrollments": ("enrollments", "enrollment_id")}
        data = {key: [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY {pk}")]
                for key, (table, pk) in tables.items()}
    return jsonify(data)


@app.errorhandler(sqlite3.OperationalError)
def unavailable_database(error):
    message = "Sample data could not be loaded. Initialize the demo database and restart the app."
    if request.path.startswith("/api/"):
        return jsonify(error=message), 503
    return render_template("setup.html", message=message, active_page=""), 503


@app.cli.command("init-db")
def init_database_command():
    # Resolve the initializer beside this file, independently of the working directory.
    import importlib.util
    spec = importlib.util.spec_from_file_location("_benefits_database_initializer", ROOT / "database.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.initialize(app.config.get("DATABASE", DB))


if __name__ == "__main__":
    app.run(debug=True)

