
INSERT INTO employees VALUES
(1, 'Rahul', 'FULL_TIME', '2026-09-01', 1),
(2, 'Priya', 'FULL_TIME', '2026-09-27', 1),
(3, 'Aman', 'PART_TIME', '2026-08-01', 1),
(4, 'Neha', 'FULL_TIME', '2026-08-01', 0),
(5, 'Ravi', 'FULL_TIME', '2026-10-28', 1),
(6, 'Sara', 'CONTRACT', '2026-08-01', 1),
(7, 'Kiran', 'FULL_TIME', '2026-08-01', 1),
(8, 'Anjali', 'FULL_TIME', '2026-08-15', 1);

INSERT INTO benefit_plans VALUES
(1, 'Medical Plus', 'FULL_TIME', 30,
 '2026-10-01', '2026-10-31', 1, 1),
(2, 'Basic Wellness', 'ANY', 0,
 '2026-10-01', '2026-10-31', 1, 0),
(3, 'Inactive Dental', 'FULL_TIME', 0,
 '2026-10-01', '2026-10-31', 0, 0);

INSERT INTO dependents VALUES
(1, 1, 'Rahul Child', 'CHILD'),
(2, 8, 'Anjali Child', 'CHILD');

INSERT INTO enrollments
(employee_id, plan_id, enrollment_date)
VALUES (7, 1, '2026-10-10');
