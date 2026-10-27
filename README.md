# Employee Benefits Administration — Configuration, Manual QA & SQL

A local Flask + SQLite lab for configuring eligibility and testing employee-benefit enrollment. All records are fictional. This is an original learning project, not Wipro's proprietary TBA system or a production HR application.

## Latest verified execution

All **30 worksheet scenarios** passed through automated Flask requests and SQLite checks; the full CI suite passed **106 tests**. [Execution report](docs/scenario_execution_report.md) · [Successful run](https://github.com/PrashantSinghpns/employee-benefits-qa/actions/runs/40518820916) · [Per-case evidence](evidence/campaign/summary.json).

The worksheet preserves its original browser/manual result fields and adds separate Scenario_Status and Automated_* columns. There are still 4 recorded agent-browser passes and 26 cases without browser/manual execution. Do not claim 30 manual UI passes.

## Features

- Active-employee and active-plan checks; configurable employment type and waiting period.
- Inclusive enrollment windows using an explicit scenario date.
- Duplicate enrollment prevention in the application and database.
- Dependent permission, ownership, and normalized duplicate-ID validation.
- Transactional enrollment writes, with rejection leaving no partial records.
- Plan configuration form and current record display.

## Run on Windows PowerShell

From the repository root, with Python 3.12 or newer installed:

```powershell
python -m venv .venv # Create an isolated project environment.
.\.venv\Scripts\python.exe -m pip install -r employee-benefits-qa/requirements.txt # Install the tested direct dependencies.
.\.venv\Scripts\python.exe employee-benefits-qa/database.py # Create the fictional baseline database.
.\.venv\Scripts\python.exe -m flask --app employee-benefits-qa/app run # Start the local application.
```

Open http://127.0.0.1:5000/ for enrollment or http://127.0.0.1:5000/configure for configuration. Stop the server with Ctrl+C. On macOS/Linux use `.venv/bin/python` in place of `.\.venv\Scripts\python.exe`.

If a database already exists, initialization stops without overwriting it. Stop the server before resetting:

```powershell
.\.venv\Scripts\python.exe employee-benefits-qa/database.py --reset # Back up the existing database, then restore the baseline.
```

The backup is saved beside the database as `benefits.db.<timestamp>.bak`. Keep it until you have verified the reset. The database, backups, and Python caches are ignored by Git.

## Reproduce verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v --junitxml=artifacts/pytest-results.xml # Run isolated automated checks.
.\.venv\Scripts\python.exe employee-benefits-qa/run_queries.py # Execute and label all 20 SQL queries against the local database.
```

The SQL runner uses the current local database. Restore the baseline first when comparing with [recorded SQL results](evidence/sql-results.txt). Automated tests use disposable databases and do not change your working database.

## Requirements and evidence

- [Requirements and rule decisions](employee-benefits-qa/docs/requirements.md)
- [Schema](employee-benefits-qa/sql/schema.sql) and [sample data](employee-benefits-qa/sql/sample_data.sql)
- [20 SQL queries](employee-benefits-qa/sql/queries.sql)
- [Test plan](docs/test_plan.md)
- [30 detailed cases with separate browser and automated results](employee-benefits-qa/docs/manual_test_cases.csv)
- [Requirements traceability](docs/traceability_matrix.csv)
- [Execution report and limitations](docs/test_execution_report.md)
- [Automated test report](docs/pytest-results.xml)
- [Reproduced and fixed ID validation defect](docs/defects/BUG-001.md)

GitHub Actions installs dependencies from the nested application folder, runs pytest from the repository root, initializes sample data, executes the SQL portfolio, and uploads the results. A workflow file alone is not proof of a successful run; inspect the run for the relevant commit.

## Scope and limitations

Use localhost and fictional data. Authentication, user roles, CSRF protection, audit history, payroll, real insurance policy rules, deployment, and load certification are outside this lab's current scope. Existing enrollments are preserved after configuration changes. SQLite SQL practice does not establish IBM DB2 experience. Browser checks performed by an agent are distinguished from pytest and from human execution in the report.

## References

Implementation patterns were checked against [Flask's tutorial](https://flask.palletsprojects.com/en/stable/tutorial/), [Flask testing](https://flask.palletsprojects.com/en/stable/testing/), [Python sqlite3](https://docs.python.org/3/library/sqlite3.html), [SQLite foreign keys](https://www.sqlite.org/foreignkeys.html), and [GitHub's Python CI guide](https://docs.github.com/en/actions/tutorials/build-and-test-code/python). Testing techniques reference the [ISTQB Foundation syllabus](https://istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf). [Microsoft's benefits documentation](https://learn.microsoft.com/en-us/dynamics365/human-resources/hr-benefits-setup-eligibility-rules) supplied domain context, not the application's exact business policy.
