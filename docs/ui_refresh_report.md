# UI repair and verification

## Problems addressed

The reported page came from a separate local API-based app with a missing stylesheet and no initialized database at its configured path. The GitHub version used another backend and schema. Mixing those files produced an unstyled page and an HTML error being parsed as JSON.

The repository now has a thin root app.py launcher for the canonical employee-benefits-qa/app.py backend. Both launch paths use the same database, templates and static assets. No database migration or deletion is performed by the launcher.

## Improvements

- Responsive enrollment and configuration pages, consistent navigation and status cards.
- Shared stylesheet and JavaScript served from explicit canonical directories.
- Readable records tables, working tabs and JSON-backed refresh.
- Selected-plan details and configuration values loaded from stored records.
- Submitted enrollment selections retained; enrollment drafts also persist in the current browser tab.
- Useful setup page and JSON error when sample data is unavailable.
- Existing business-rule and scenario tests preserved.

## Actual verification

114 pytest executions passed locally on Windows/Python 3.14. This includes eight additional UI/asset/setup checks and all 30 automated worksheet scenarios. JavaScript syntax was checked with Node.

Agent-operated browser checks on the candidate build:
1. Desktop page loaded with its stylesheet and complete layout.
2. Switching enrollment plan updated coverage details.
3. Refresh records returned data and showed an up-to-date message, without a JSON parser error.
4. Opening Basic Wellness loaded ANY eligibility, zero waiting days and disabled dependent coverage; switching to Medical Plus loaded its own saved settings.
5. Anjali/Basic Wellness/2026-10-12 saved successfully and retained all three submitted values.
6. An unsaved Anjali/Basic Wellness/2026-10-13 draft survived a fresh GET in the same tab.
7. A 390-pixel-wide iframe preview exercised the small-screen CSS layout. This was a responsive visual check, not a claim of testing on a physical phone.

The earlier CSV execution history remains unchanged. These checks do not convert historical unexecuted manual cases into manual passes. CI results must be read from the workflow run for the published commit.

## Run the corrected version

For a clean copy, install root requirements.txt, initialize with `python -m flask --app app init-db`, then run `python app.py`. The older `python employee-benefits-qa/app.py` command also reaches the same backend. Open http://127.0.0.1:5000/ through Flask; do not open an HTML file directly.

Existing initialized canonical databases are retained. Initialization refuses to overwrite them; do not use --reset merely to install this UI update. Previously created root API databases and root SQL copies are not used by the canonical launcher.
