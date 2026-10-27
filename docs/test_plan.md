# Test plan

## Objective and scope

Verify requirements R01–R12: record display, active status, employment-type eligibility, waiting periods, inclusive enrollment windows, duplicates, invalid inputs, dependent ownership/permission, configuration validation, and atomic writes. Test the Flask forms, business function, and SQLite constraints. Assess impact in terms of incorrect benefit access, rejected eligible employees, duplicate records, or partial enrollment.

## Test environment

Local Windows/Python 3.14 with Flask 3.1.3, pytest 9.1.0 and SQLite. CI targets Ubuntu/Python 3.12. The execution report records what was actually run. Use fictional sample records only. Tests create isolated temporary or in-memory databases; browser cases use the working sample database.

## Entry criteria

- Dependencies install and schema/sample scripts initialize a new database.
- Numbered requirements and expected business outcomes are available.
- Record the application commit or identify a local pre-publication working version.

## Techniques and priority

Use equivalence partitions for status/types/IDs, boundary values for dates and waiting days, and combinations of eligibility conditions. Prioritize wrong eligibility, duplicates, ownership, and rollback. Smoke checks open both pages, accept a valid enrollment, and reject an invalid one. Configuration changes require regression checks of subsequent submissions and preservation of existing records.

## Data and reset

Restore the baseline before each independent case: stop the server, run `python employee-benefits-qa/database.py --reset`, then restart. The reset makes a timestamped backup. Never reset a real HR database. For TC15, use Kiran's seeded enrollment or explicitly record the preceding enrollment used. For TC22 inject the documented trigger in a disposable database and remove it afterwards. Store screenshots and SQL outputs under evidence/.

## Execution and reporting

Use the detailed CSV, including exact data, setup, steps and database oracle. Leave Actual_Result blank until observed. Status is Not Run, Pass, Fail or Blocked. Identify operator and method: human browser, agent browser, or automated test. Pytest does not turn a manual case into a manual pass. Keep original failure evidence and append retest results. Report counts separately and trace every requirement to actual test names and SQL checks.

## Defect handling

Reproduce, assess customer impact/severity, record expected/actual behavior and environment, fix, retest, and run regression. Use defect_template.md for new findings; numbered reports must contain actual findings. A review mismatch after configuration change is not automatically a defect because existing enrollments are preserved.

## Exit criteria

Automated suite passes, all 20 queries execute against the baseline, application paths have meaningful assertions, and planned manual cases have been executed or explicitly remain outstanding with reasons. No unresolved high-impact enrollment defect. Fresh setup instructions work. Completion of code fixes does not imply completion of the manual campaign.

## Risks and exclusions

Sample data is small; successful checks do not establish production readiness, browser compatibility, stress capacity or DB2 expertise. Manual cases requiring crafted requests or controlled faults cannot be performed solely with the ordinary form controls. Keep that evidence separate from normal UI checks. Authentication, authorization and production deployment are outside the present local lab.
