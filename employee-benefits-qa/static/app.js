// Enhancement only: server-rendered forms and records remain usable without JavaScript.
const dataElement = document.querySelector('#page-data');
let records = dataElement ? JSON.parse(dataElement.textContent) : null;

const enrollmentForm = document.querySelector('#enrollment-form');
const draftKey = 'benefits-lab:enrollment:v3';
function rememberEnrollment() {
  if (!enrollmentForm) return;
  try {
    const data = new FormData(enrollmentForm);
    const draft = Object.fromEntries(data);
    draft.dependent_ids = data.getAll('dependent_ids');
    sessionStorage.setItem(draftKey, JSON.stringify(draft));
  } catch { /* Optional tab storage must never prevent enrollment. */ }
}

if (enrollmentForm) {
  try {
    // POST responses show what was submitted; fresh GETs can restore the last draft in this tab.
    if (enrollmentForm.dataset.submitted === 'true') {
      rememberEnrollment();
    } else {
      const draft = JSON.parse(sessionStorage.getItem(draftKey) || 'null');
      if (draft && typeof draft === 'object') {
        for (const field of enrollmentForm.elements) {
          if (!field.name) continue;
          if (field.type === 'checkbox') {
            field.checked = Array.isArray(draft[field.name]) && draft[field.name].includes(field.value);
          } else if (typeof draft[field.name] === 'string') {
            if (field.tagName !== 'SELECT' || [...field.options].some(option => option.value === draft[field.name])) {
              field.value = draft[field.name];
            }
          }
        }
      }
    }
  } catch { /* Ignore unavailable storage or a malformed old draft. */ }
  enrollmentForm.addEventListener('input', rememberEnrollment);
  enrollmentForm.addEventListener('change', rememberEnrollment);
  enrollmentForm.addEventListener('submit', rememberEnrollment);
}

function showPlan() {
  const selector = document.querySelector('#enrollment-plan');
  if (!selector || !records) return;
  const plan = records.plans.find(item => String(item.plan_id) === selector.value);
  if (!plan) return;
  document.querySelector('#plan-name').textContent = plan.name;
  const status = document.querySelector('#plan-status');
  status.textContent = plan.active ? 'Active coverage' : 'Inactive plan';
  status.classList.toggle('inactive', !plan.active);
  document.querySelector('#plan-type').textContent = plan.eligible_type === 'ANY' ? 'All employment types' : plan.eligible_type.replaceAll('_', ' ').toLowerCase();
  document.querySelector('#plan-waiting').textContent = `${plan.waiting_days} calendar days`;
  document.querySelector('#plan-window').textContent = `${plan.window_start} → ${plan.window_end}`;
  document.querySelector('#plan-dependents').textContent = plan.allow_dependents ? 'Included' : 'Not included';
  document.querySelector('#edit-selected-plan').href = `/configure?plan_id=${encodeURIComponent(plan.plan_id)}`;
}

document.querySelector('#enrollment-plan')?.addEventListener('change', showPlan);
showPlan();

document.querySelector('#configuration-plan')?.addEventListener('change', event => {
  // Load saved values for the newly chosen plan, rather than retaining another plan's fields.
  window.location.assign(`/configure?plan_id=${encodeURIComponent(event.target.value)}`);
});

for (const tab of document.querySelectorAll('[data-table]')) {
  tab.addEventListener('click', () => {
    for (const item of document.querySelectorAll('[data-table]')) {
      const selected = item === tab;
      item.classList.toggle('selected', selected);
      item.setAttribute('aria-selected', String(selected));
      document.querySelector(`#panel-${item.dataset.table}`).hidden = !selected;
    }
  });
}

function renderTable(target, rows, name) {
  target.replaceChildren();
  if (!rows.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = `No ${name} yet.`;
    target.append(empty);
    return;
  }
  // Keep column order stable before and after refreshing JSON data.
  const preferred = {
    employees: ['employee_id', 'name', 'employment_type', 'hire_date', 'active'],
    plans: ['plan_id', 'name', 'eligible_type', 'waiting_days', 'window_start', 'window_end', 'active', 'allow_dependents'],
    enrollments: ['enrollment_id', 'employee_id', 'plan_id', 'enrollment_date', 'created_at'],
    dependents: ['dependent_id', 'employee_id', 'name', 'relationship']
  };
  const columns = preferred[name] || Object.keys(rows[0]);
  const table = document.createElement('table');
  const header = document.createElement('thead');
  const heading = document.createElement('tr');
  for (const column of columns) {
    const cell = document.createElement('th');
    cell.scope = 'col';
    cell.textContent = column.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase());
    heading.append(cell);
  }
  header.append(heading);
  const body = document.createElement('tbody');
  for (const row of rows) {
    const line = document.createElement('tr');
    for (const column of columns) {
      const cell = document.createElement('td');
      cell.textContent = String(row[column] ?? ''); // Treat record values as text, never HTML.
      line.append(cell);
    }
    body.append(line);
  }
  table.append(header, body);
  target.append(table);
}

document.querySelector('#refresh-records')?.addEventListener('click', async event => {
  const button = event.currentTarget;
  const status = document.querySelector('#records-status');
  button.disabled = true;
  status.textContent = 'Refreshing records…';
  try {
    const response = await fetch('/api/data', {cache: 'no-store'});
    // A missing route or server error must produce a clear message, not a JSON parser exception.
    if (!response.headers.get('content-type')?.includes('application/json')) {
      throw new Error('The records service is unavailable. Restart the app using the project launcher.');
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Records could not be loaded.');
    for (const name of ['employees', 'plans', 'enrollments', 'dependents']) {
      if (!Array.isArray(data[name])) throw new Error('The records service returned an unexpected format.');
    }
    records = data;
    for (const name of ['employees', 'plans', 'enrollments', 'dependents']) {
      renderTable(document.querySelector(`[data-table-content="${name}"]`), data[name], name);
      for (const count of document.querySelectorAll(`[data-count="${name}"]`)) count.textContent = data[name].length;
    }
    showPlan();
    status.textContent = 'Records are up to date.';
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
