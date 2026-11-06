WEEKLY REPORT-9
Project Title: AI-Powered Business Intelligence Platform
Student ID: 23DCS110, 23DCS106
Semester: 7th

From Date: 08/09/2026    To Date: 14/09/2026

Work done from Date: 08/09/2026 to 14/09/2026
(Attach supporting documents)

- Tested the CSV upload workflow, schema detection, data cleaning, database loading, KPI generation, and dashboard display.
- Checked dashboard charts, date and category filters, KPI period comparisons, chat history, and PDF report export.
- Confirmed that a sample uploaded dataset could be processed and its resulting analytics displayed in the frontend.
- Reviewed pipeline and anomaly notification behavior during upload testing.
- Recorded a database schema mismatch affecting notification persistence for follow-up.
- Recorded a PostgreSQL numeric-rounding error in one generated analytical view for follow-up.
- Reviewed local authentication, CORS, and environment configuration while testing the frontend-to-backend connection.
- Updated the project notes with tested workflows and the issues found.

Plans for next week: Date: 15/09/2026 to 21/09/2026

- Improve the dataset inspection experience so users can visually explore detected tables, columns, and quality information.
- Review profile and dataset-history workflows and identify useful user-facing improvements.
- Replace inactive or unsuitable interface options with controls that affect actual application behavior.
- Remove authentication-provider buttons that do not have a working provider integration.
- Retest upload, dashboard, authentication, and frontend/backend connectivity after changes.
- Run focused regression tests and record any unresolved database issues.

References:

- FastAPI Documentation – https://fastapi.tiangolo.com/
- PostgreSQL Documentation – https://www.postgresql.org/docs/
- React Documentation – https://react.dev/
- Vite Documentation – https://vite.dev/guide/
- SQLAlchemy Documentation – https://docs.sqlalchemy.org/
- Pandas Documentation – https://pandas.pydata.org/docs/

Signature of Student: ____________________
Signature of Mentor: ____________________


WEEKLY REPORT-10
Project Title: AI-Powered Business Intelligence Platform
Student ID: 23DCS110, 23DCS106
Semester: 7th

From Date: 15/09/2026    To Date: 21/09/2026

Work done from Date: 15/09/2026 to 21/09/2026
(Attach supporting documents)

- Investigated the frontend upload error and traced it to mismatched local API host/port configuration and CORS origin settings.
- Aligned the frontend API URL with the active backend service and added a configurable API base URL for later hosting.
- Added and reviewed backend health/readiness checks and production configuration requirements.
- Tested CSV upload directly against the API and confirmed the ETL workflow completed and returned analytics.
- Recorded database compatibility issues found during upload testing: notification persistence expected a missing column, and one generated view produced a PostgreSQL numeric-rounding error.
- Reviewed authentication behavior and confirmed that sign-up/sign-in endpoints are separate from the setting that protects other API routes.
- Ran the backend test suite and frontend build after the connectivity and configuration changes.

Plans for next week: Date: 22/09/2026 to 28/09/2026

- Add Data X-Ray so users can visually inspect tables, fields, types, quality signals, and detected relationships.
- Improve profile and dataset-history workflows, including editable dataset names.
- Replace inactive dashboard settings with preferences that visibly affect dashboard behavior.
- Remove sign-in controls that do not have an implemented identity-provider integration.
- Test upload, dashboard, profile, history, and authentication flows after the frontend changes.
- Run backend tests, frontend type validation, and a production build.

References:

- FastAPI Documentation – https://fastapi.tiangolo.com/
- PostgreSQL Documentation – https://www.postgresql.org/docs/
- React Documentation – https://react.dev/
- Vite Documentation – https://vite.dev/guide/
- SQLAlchemy Documentation – https://docs.sqlalchemy.org/
- Pandas Documentation – https://pandas.pydata.org/docs/

Signature of Student: ____________________
Signature of Mentor: ____________________


WEEKLY REPORT-11
Project Title: AI-Powered Business Intelligence Platform
Student ID: 23DCS110, 23DCS106
Semester: 7th

From Date: 22/09/2026    To Date: 28/09/2026

Work done from Date: 22/09/2026 to 28/09/2026
(Attach supporting documents)

- Added the Data X-Ray page to visualize detected tables, fields, data types, missing values, quality scores, sample values, and relationships.
- Added field-level inspection so a selected column shows its profile and the quality details for its table.
- Updated dashboard settings to use working preferences, including default date range, KPI number format, and executive-summary visibility.
- Added a Profile page with account information and display-name editing.
- Added persistent dataset names and inline rename controls to Dataset History.
- Removed Google/GitHub sign-in controls and inactive Remember me/Forgot password options because their provider/reset flows are not implemented.
- Tested sign-up, sign-in, profile/settings access, and session renaming against the local database.
- Ran the backend regression suite successfully: 61 tests passed. Frontend type validation and the production build also passed.

Plans for next week: Date: 29/09/2026 to 05/10/2026

- Implement a public read-only dashboard view that displays the shared dataset's name, KPI values, saved insights, and aggregate charts.
- Validate share-token access and expiration, and exclude sampled chart data from public responses.
- Test production-mode sign-up/sign-in, bearer-token access, and protected API behavior.
- Improve handling of empty AI-generated SQL responses while preserving read-only query validation.
- Run full backend tests, frontend type validation, production build, and live integration checks.
- Prepare the frontend/backend deployment configuration and record hosted-service requirements.

References:

- FastAPI Documentation – https://fastapi.tiangolo.com/
- PostgreSQL Documentation – https://www.postgresql.org/docs/
- React Documentation – https://react.dev/
- Vite Documentation – https://vite.dev/guide/
- SQLAlchemy Documentation – https://docs.sqlalchemy.org/
- Plotly Documentation – https://plotly.com/javascript/

Signature of Student: ____________________
Signature of Mentor: ____________________


WEEKLY REPORT-12
Project Title: AI-Powered Business Intelligence Platform
Student ID: 23DCS110, 23DCS106
Semester: 7th

From Date: 29/09/2026    To Date: 05/10/2026

Work done from Date: 29/09/2026 to 05/10/2026
(Attach supporting documents)

- Updated the public shared dashboard to return a dataset title, KPI values, saved insights, and aggregate chart data.
- Verified that a share token opens the associated dashboard without requiring the viewer to sign in.
- Kept public responses read-only and excluded chart types that may reveal sampled individual values.
- Corrected the production-authentication rule so production and staging require authentication even if REQUIRE_AUTH is accidentally set to false.
- Added automatic bearer-token attachment to frontend API requests so signed-in users can access protected routes.
- Tested the authentication flow in production mode: unauthenticated API requests were rejected, while sign-up, sign-in, profile access, and authenticated session access succeeded.
- Improved AI SQL generation handling for empty provider responses by retrying and returning a clearer error if no SQL is received.
- Kept generated SQL restricted to validated read-only SELECT queries.
- Ran the full backend suite successfully: 65 tests passed. The frontend typecheck and Vercel-targeted production build also succeeded.

Plans for next week: Date: 06/10/2026 to 12/10/2026

- Add session-ownership checks to protected data routes and associate each new upload session with its signed-in owner.
- Filter session history and session-level access according to ownership.
- Add KPI confidence context and a percentage-based what-if calculation endpoint.
- Add focused test coverage for session ownership, empty AI responses, KPI confidence, and scenario calculations.
- Preserve the read-only SELECT validation in the AI query flow while making these changes.

References:

- FastAPI Documentation – https://fastapi.tiangolo.com/
- PostgreSQL Documentation – https://www.postgresql.org/docs/
- React Documentation – https://react.dev/
- Vite Documentation – https://vite.dev/guide/
- SQLAlchemy Documentation – https://docs.sqlalchemy.org/
- Plotly Documentation – https://plotly.com/javascript/

Signature of Student: ____________________
Signature of Mentor: ____________________
