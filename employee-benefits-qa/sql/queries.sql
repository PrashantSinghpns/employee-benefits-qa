
-- Q01: Show all active employees
SELECT * FROM employees WHERE active = 1;

-- Q02: Find full-time employees
SELECT name, hire_date
FROM employees
WHERE employment_type = 'FULL_TIME';

-- Q03: Show active benefit plans
SELECT name, waiting_days
FROM benefit_plans
WHERE active = 1;

-- Q04: Find plans open on October 27
SELECT name
FROM benefit_plans
WHERE active = 1
AND '2026-10-27' BETWEEN window_start AND window_end;

-- Q05: Calculate eligibility date
SELECT e.name, p.name AS plan,
       date(e.hire_date,
            '+' || p.waiting_days || ' days') AS eligible_date
FROM employees e
CROSS JOIN benefit_plans p
WHERE p.plan_id = 1;

-- Q06: Employees still in waiting period
SELECT e.name
FROM employees e
JOIN benefit_plans p ON p.plan_id = 1
WHERE date(e.hire_date,
      '+' || p.waiting_days || ' days') > '2026-10-27';

-- Q07: Eligible employee-plan pairs on October 27
SELECT e.name, p.name AS plan
FROM employees e
CROSS JOIN benefit_plans p
WHERE e.active = 1
AND p.active = 1
AND (p.eligible_type = 'ANY'
     OR e.employment_type = p.eligible_type)
AND '2026-10-27' >= date(
    e.hire_date, '+' || p.waiting_days || ' days')
AND '2026-10-27' BETWEEN p.window_start AND p.window_end
AND NOT EXISTS (
    SELECT 1 FROM enrollments en
    WHERE en.employee_id = e.employee_id
      AND en.plan_id = p.plan_id
);

-- Q08: Show employee enrollments (JOIN)
SELECT e.name AS employee, p.name AS plan,
       en.enrollment_date
FROM enrollments en
JOIN employees e ON e.employee_id = en.employee_id
JOIN benefit_plans p ON p.plan_id = en.plan_id;

-- Q09: Show employees and their dependents
SELECT e.name AS employee, d.name AS dependent
FROM employees e
JOIN dependents d ON e.employee_id = d.employee_id;

-- Q10: Show enrolled dependents
SELECT e.name AS employee,
       d.name AS dependent,
       p.name AS plan
FROM enrollment_dependents ed
JOIN enrollments en
  ON ed.enrollment_id = en.enrollment_id
JOIN employees e ON en.employee_id = e.employee_id
JOIN benefit_plans p ON en.plan_id = p.plan_id
JOIN dependents d ON ed.dependent_id = d.dependent_id;


-- Q11: Count enrollments for each plan
SELECT p.name, COUNT(en.enrollment_id) AS total
FROM benefit_plans p
LEFT JOIN enrollments en ON p.plan_id = en.plan_id
GROUP BY p.plan_id, p.name;

-- Q12: Enrollments by employment type
SELECT e.employment_type,
       COUNT(en.enrollment_id) AS total
FROM employees e
LEFT JOIN enrollments en
  ON e.employee_id = en.employee_id
GROUP BY e.employment_type;

-- Q13: Plans with more than 1 enrollment
SELECT p.name, COUNT(*) AS total
FROM enrollments en
JOIN benefit_plans p ON en.plan_id = p.plan_id
GROUP BY p.plan_id, p.name
HAVING COUNT(*) > 1;

-- Q14: Employees without enrollments
SELECT e.name
FROM employees e
LEFT JOIN enrollments en
  ON e.employee_id = en.employee_id
WHERE en.enrollment_id IS NULL;

-- Q15: Plans without enrollments
SELECT p.name
FROM benefit_plans p
WHERE NOT EXISTS (
    SELECT 1 FROM enrollments en
    WHERE en.plan_id = p.plan_id
);

-- Q16: Employees enrolled in multiple plans
SELECT e.name,
       COUNT(DISTINCT en.plan_id) AS plan_count
FROM employees e
JOIN enrollments en
  ON e.employee_id = en.employee_id
GROUP BY e.employee_id, e.name
HAVING COUNT(DISTINCT en.plan_id) > 1;

-- Q17: Detect duplicate employee-plan enrollments
SELECT employee_id, plan_id, COUNT(*) AS total
FROM enrollments
GROUP BY employee_id, plan_id
HAVING COUNT(*) > 1;

-- Q18: Detect orphan enrollment records
SELECT en.enrollment_id
FROM enrollments en
LEFT JOIN employees e
  ON en.employee_id = e.employee_id
LEFT JOIN benefit_plans p
  ON en.plan_id = p.plan_id
WHERE e.employee_id IS NULL
   OR p.plan_id IS NULL;

-- Q19: Detect incorrect dependent ownership
SELECT en.enrollment_id, d.dependent_id
FROM enrollment_dependents ed
JOIN enrollments en
  ON ed.enrollment_id = en.enrollment_id
JOIN dependents d
  ON ed.dependent_id = d.dependent_id
WHERE en.employee_id <> d.employee_id;

-- Q20: Find enrollments conflicting with current rules
SELECT en.enrollment_id,
       e.name AS employee,
       p.name AS plan
FROM enrollments en
JOIN employees e ON en.employee_id = e.employee_id
JOIN benefit_plans p ON en.plan_id = p.plan_id
WHERE e.active = 0
   OR p.active = 0
   OR (p.eligible_type <> 'ANY'
       AND e.employment_type <> p.eligible_type)
   OR en.enrollment_date < date(
       e.hire_date, '+' || p.waiting_days || ' days')
   OR en.enrollment_date NOT BETWEEN
       p.window_start AND p.window_end;
