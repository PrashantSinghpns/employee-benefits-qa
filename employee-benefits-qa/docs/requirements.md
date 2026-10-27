
# Employee Benefits System — Requirements

R01: Display employees, plans, dependents and enrollments.

R02: Reject inactive employees.

R03: Reject inactive benefit plans.

R04: Employment type must match plan eligibility
     (FULL_TIME, PART_TIME, CONTRACT or ANY).

R05: Waiting period must be completed before enrollment.

R06: Enrollment date must be within the plan window,
     including the start and end dates.

R07: Prevent duplicate employee-plan enrollments.

R08: Reject missing, invalid or nonexistent IDs and dates.

R09: Allow dependents only if the plan permits them.

R10: Dependents must belong to the enrolling employee.

R11: Validate plan configuration before saving changes.

R12: Save enrollment and dependent records together,
     or save neither if an error occurs.

## Additional Rules
- Waiting period: 0 to 365 days.
- Employees cannot enroll before their hire date.
- End date cannot precede start date.
- A one-day enrollment window is valid.
- Employees may enroll in multiple different plans.
- Duplicate dependent IDs in one request are rejected.
- Configuration changes affect future enrollment attempts.
- Existing enrollments remain after configuration changes.
- Entered enrollment dates are scenario dates for testing.
