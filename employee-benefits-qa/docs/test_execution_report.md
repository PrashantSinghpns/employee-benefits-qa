# Latest execution status

The [worksheet campaign report](scenario_execution_report.md) records the latest verified execution: **30/30 automated worksheet scenarios passed; 106/106 full-suite tests passed** on [GitHub Actions](https://github.com/PrashantSinghpns/employee-benefits-qa/actions/runs/40518820916). Per-case request and database evidence is committed under evidence/campaign/.

The CSV retains the original 4 browser passes and 26 unexecuted browser/manual cases, with separate Automated_* result columns for all 30 scenarios. Automated scenario coverage is complete for this worksheet; manual/browser execution remains a separate record. No human manual execution is claimed.

---

The following is the historical local verification report. Its 69-test XML and four browser checks predate the latest CI campaign.

# Test execution report

## Version and environment
Base reviewed commit: 9db0e15d4ce3856d37c1109fc9a707c65aaa86db.
Results below apply to the local candidate with the fixes and added tests in this change. The GitHub Actions run binds its own report to the published commit.
Execution date: October 27, 2026, Asia/Kolkata.
Local environment: Windows, Python 3.14, Flask 3.1.3, pytest 9.1.0, SQLite.
CI target: Ubuntu, Python 3.12.

## Automated execution
Original repository suite independently rerun: 26 passed.
Expanded suite: 69 collected, 69 passed, 0 failed, 0 errors, 0 skipped.
Command: python -m pytest tests -q --junitxml=docs/pytest-results.xml
Evidence: [JUnit XML](pytest-results.xml).
Includes form submissions, invalid IDs/dates/configurations, inclusive boundaries, application rollback, baseline SQL results, and initialization/reset backups.
The first candidate run found a Windows file-locking issue in the new reset helper; after explicit connection cleanup the complete suite passed. The uploaded XML records the final run.

## Browser campaign
Planned cases: 30.
Executed through observed browser controls by an agent: 4.
Passed: 4. Failed: 0. Remaining Not Run: 26.
Executed: TC08 waiting rejection; TC09 exact waiting boundary; TC15 repeated Priya enrollment; TC25 configure ANY and enroll Aman.
TC15 deliberately follows TC09 instead of using the seeded Kiran enrollment; the actual inputs are recorded in the CSV.
Evidence: [browser check log](browser_checks.json) and screenshots under evidence/.
Human manual executions are not claimed. Automated test outcomes were not copied into manual-result fields.
Worksheet: ../employee-benefits-qa/docs/manual_test_cases.csv

## SQL execution
20 query statements executed against a freshly restored baseline.
Evidence: ../evidence/sql-results.txt.
Baseline row counts Q01-Q20:
7, 6, 2, 2, 8, 1, 9, 1, 2, 0, 3, 3, 0, 7, 2, 0, 0, 0, 0, 0.
Zero-row integrity results alone do not prove detection of every possible corrupt record.
Q20 reports current-rule conflicts for review; configuration changes do not automatically invalidate historical enrollments.

## CI
The workflow now uses the correct nested requirements path and uploads pytest/SQL evidence.
Consult the PR checks / Actions page for the result of the published commit. Local success is not a claim that a remote workflow passed.

## Defects and remaining work
BUG-001 (oversized IDs): reproduced and fixed, automated retest passed.
The former empty numbered defect file has been replaced by this genuine finding; a separate reusable template is available.
Remaining: execute the other 26 browser/manual cases, including prepared requests and the controlled-fault scenario where required. Capture the operator, version, actual outcome and evidence.
Overall: code fixes and automated verification complete for this candidate; the full manual campaign remains incomplete.
