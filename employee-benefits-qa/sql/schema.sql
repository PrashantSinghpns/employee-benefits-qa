
PRAGMA foreign_keys = ON;

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    employment_type TEXT NOT NULL
        CHECK (employment_type IN
        ('FULL_TIME', 'PART_TIME', 'CONTRACT')),
    hire_date TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
        CHECK (active IN (0, 1))
);

CREATE TABLE benefit_plans (
    plan_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    eligible_type TEXT NOT NULL
        CHECK (eligible_type IN
        ('FULL_TIME', 'PART_TIME', 'CONTRACT', 'ANY')),
    waiting_days INTEGER NOT NULL
        CHECK (waiting_days BETWEEN 0 AND 365),
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
        CHECK (active IN (0, 1)),
    allow_dependents INTEGER NOT NULL DEFAULT 0
        CHECK (allow_dependents IN (0, 1)),
    CHECK (window_end >= window_start)
);

CREATE TABLE dependents (
    dependent_id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    relationship TEXT NOT NULL,
    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE enrollments (
    enrollment_id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    plan_id INTEGER NOT NULL,
    enrollment_date TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (employee_id, plan_id),
    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id),
    FOREIGN KEY (plan_id)
        REFERENCES benefit_plans(plan_id)
);

CREATE TABLE enrollment_dependents (
    enrollment_id INTEGER NOT NULL,
    dependent_id INTEGER NOT NULL,
    PRIMARY KEY (enrollment_id, dependent_id),
    FOREIGN KEY (enrollment_id)
        REFERENCES enrollments(enrollment_id),
    FOREIGN KEY (dependent_id)
        REFERENCES dependents(dependent_id)
);
