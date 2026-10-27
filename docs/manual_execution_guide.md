# Execute the outstanding manual cases

Use the detailed worksheet. Restore the fictional baseline between independent cases using database.py --reset (stop the server first), then restart. Record the date, tested commit, exact inputs, actual message, relevant database rows, and screenshot/request evidence. Never mark a case passed solely because a related pytest test passed.

Ordinary browser cases: open / or /configure and use the named records and dates in Test_Data. After a configuration submission the form clears; inspect stored plan data under Current records to verify what was saved. Existing enrollments are preserved by policy.

Prepared-request cases TC17-TC19 and TC21: use an HTTP request client against localhost POST / with application/x-www-form-urlencoded fields employee_id, plan_id, enrollment_date and repeated dependent_ids. Omit employee_id for TC17; use 999 for TC18; use 2026-02-30 for TC19; use dependent_ids=1 and dependent_ids=01 for TC21. These cannot all be represented by the normal browser controls. Record the method as a request check rather than an ordinary browser action.

TC16: a rapid browser repeat does not prove concurrent request handling. Check record counts and separately describe any concurrent test actually performed.

TC22: in a disposable baseline database create this trigger before submitting Rahul with his child:

```sql
-- Force the dependent insert to fail after the enrollment insert, exercising rollback.
CREATE TRIGGER reject_dependent BEFORE INSERT ON enrollment_dependents
BEGIN SELECT RAISE(ABORT, 'controlled test failure'); END;
```

Expected: no new enrollment and no dependent links. Remove the trigger after inspection:

```sql
DROP TRIGGER reject_dependent; -- Restore normal writes after the controlled-fault check.
```

The automated test test_application_rolls_back_on_dependent_insert_failure already executes this application path. Keep its outcome separate from the manually directed campaign.

Useful database oracles: Q08 shows enrollments, Q10 shows selected dependent links, Q17 checks duplicates, Q19 checks ownership. Check raw counts before and after rejected submissions. Save outputs with the database setup and application version used.
