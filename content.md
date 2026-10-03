WEEKLY REPORT-9
Project Title: AI-Powered Business Intelligence Platform
Student ID: 23DCS110, 23DCS106
Semester: 7th

From Date: 08/09/2026  To Date: 14/09/2026

Work done from Date: 08/09/2026 to 14/09/2026
(Attach supporting documents)

Performed end-to-end testing of CSV upload, schema detection, data cleaning, database loading, KPI generation, and dashboard display.
Tested dashboard charts, date and category filters, KPI period comparisons, chat history, and PDF report export.
Verified that uploaded datasets could be processed and that resulting analytics were available through the frontend.
Reviewed notification behavior for pipeline completion and detected anomalies.
Identified a database schema mismatch affecting notification persistence and recorded it for follow-up.
Identified a PostgreSQL numeric rounding issue in one generated analytical view and documented it for correction.
Reviewed authentication, CORS, and production configuration as part of the project safety checks.
Updated project documentation with the tested workflows and remaining integration issues.
Plans for next week: Date: 15/09/2026 to 21/09/2026

Complete the machine-learning training workflow for customer churn, revenue forecasting, and customer segmentation.
Connect model training and artifact storage to the backend API.
Test model input validation and error handling with prepared datasets.
Continue resolving the database compatibility issues found during end-to-end testing.
Verify that frontend API configuration and backend CORS settings work together during upload and dashboard use.
Run regression tests after the ML and backend changes.
References:

FastAPI Documentation – https://fastapi.tiangolo.com/
PostgreSQL Documentation – https://www.postgresql.org/docs/
React Documentation – https://react.dev/
Vite Documentation – https://vite.dev/guide/
SQLAlchemy Documentation – https://docs.sqlalchemy.org/
Pandas Documentation – https://pandas.pydata.org/docs/













Project Title: AI-Powered Business Intelligence Platform
Student ID: 23DCS110, 23DCS106
Semester: 7th

From Date: 15/09/2026  To Date: 21/09/2026

Work done from Date: 15/09/2026 to 21/09/2026
(Attach supporting documents)

Converted the churn, forecasting, and customer-segmentation model placeholders into reusable Python training functions.
Implemented churn model training and prediction support using customer feature data.
Implemented monthly revenue forecasting with forecast result and model artifact output.

Implemented RFM-based customer segmentation with saved model and scaler artifacts.
Added a backend API endpoint for training supported models from prepared CSV files.
Added input validation for required model columns and insufficient training data.
Investigated and corrected a backend import issue that prevented the API from starting.
Resolved local frontend-to-backend connectivity by aligning API address, port, and CORS configuration.
Tested upload and dashboard access after restoring the local API connection.
Plans for next week: Date: 22/09/2026 to 28/09/2026

Add a visual dataset inspection page using schema, column, relationship, and data-quality information.
Improve account and dataset management workflows in the frontend.
Replace settings that do not affect the application with practical dashboard preferences.
Remove authentication options that are displayed but not implemented.
Test new features with existing upload and dashboard workflows.
Run backend tests, frontend type checks, and a production build.
References:

FastAPI Documentation – https://fastapi.tiangolo.com/
PostgreSQL Documentation – https://www.postgresql.org/docs/
React Documentation – https://react.dev/
Vite Documentation – https://vite.dev/guide/
SQLAlchemy Documentation – https://docs.sqlalchemy.org/
Scikit-learn Documentation – https://scikit-learn.org/stable/
Prophet Documentation – https://facebook.github.io/prophet/
Signature of Student:





Project Title: AI-Powered Business Intelligence Platform
Student ID: 23DCS110, 23DCS106
Semester: 7th

From Date: 22/09/2026  To Date: 28/09/2026

Work done from Date: 22/09/2026 to 28/09/2026
(Attach supporting documents)

Added the Data X-Ray page to visualize detected tables, fields, data types, missing values, quality scores, sample values, and table relationships.
Added field inspection so users can select a column and view its profile and quality details.
Updated dashboard settings to use meaningful options, including default date range, KPI number format, and executive-summary visibility.
Added a Profile page showing account information and allowing the user to update their display name.
Added persistent dataset names and inline rename controls to dataset history.
Removed Google and GitHub sign-in controls because those authentication providers are not implemented.
Removed inactive “Remember me” and “Forgot password?” controls from the sign-in page.
Tested signup, sign-in, profile loading, settings updates, and dataset renaming against the local database.
Ran the backend regression suite successfully: 61 tests passed.
Verified the frontend TypeScript check and production build.
Plans for next week: Date: 29/09/2026 to 05/10/2026

Perform complete end-to-end testing of upload, ETL, dashboard, Data X-Ray, profile, history, AI chat, and PDF reporting.
Validate public read-only dashboard sharing, including token access and expired or invalid links.
Review the database notification and analytical-view issues found during upload testing and verify their status.
Test the application with multiple datasets and confirm that dataset-specific information remains correctly separated.
Prepare the deployment configuration, including database, authentication, CORS, and frontend API settings.
Record any remaining issues and prepare the final deployment and testing reports.
References:

FastAPI Documentation – https://fastapi.tiangolo.com/
PostgreSQL Documentation – https://www.postgresql.org/docs/
React Documentation – https://react.dev/
Vite Documentation – https://vite.dev/guide/
SQLAlchemy Documentation – https://docs.sqlalchemy.org/
Pandas Documentation – https://pandas.pydata.org/docs/











Project Title: AI-Powered Business Intelligence Platform
Student ID: 23DCS110, 23DCS106
Semester: 7th

From Date: 29/09/2026  To Date: 05/10/2026

Work done from Date: 29/09/2026 to 05/10/2026
(Attach supporting documents)

Enhanced public dashboard sharing so a generated link opens a named, read-only dashboard page.
Added KPI cards, saved insights, and generated aggregate charts to the public shared view.
Kept public access token-based, with a seven-day expiry and hashed token storage.
Restricted shared chart output to aggregate chart types and excluded scatter, histogram, and box charts that may expose sampled individual values.
Verified that a shared dashboard returns its dataset name, KPI information, and aggregate chart data without requiring the viewer to sign in.
Tested the public share flow using temporary test data and removed the temporary database records after verification.
Ran the full backend test suite successfully: 61 tests passed.
Verified the frontend TypeScript check and production build after the sharing changes.
Updated the presentation draft to describe the implemented public dashboard accurately.

Plans for next week: Date: 06/10/2026 to 12/10/2026

Complete end-to-end testing of upload, ETL, analytics, Data X-Ray, AI chat, PDF reporting, and public dashboard sharing.
Verify invalid and expired share-link behavior and document the seven-day expiry limitation.
Review and retest the previously observed notification-schema and PostgreSQL analytical-view issues.
Test several datasets and verify that each share link returns only data for its associated session.
Prepare deployment configuration and document database, authentication, CORS, and frontend API requirements.
Record remaining limitations and prepare the final testing and deployment progress reports.

References:

FastAPI Documentation – https://fastapi.tiangolo.com/
PostgreSQL Documentation – https://www.postgresql.org/docs/
React Documentation – https://react.dev/
Vite Documentation – https://vite.dev/guide/
SQLAlchemy Documentation – https://docs.sqlalchemy.org/
Pandas Documentation – https://pandas.pydata.org/docs/
Plotly Documentation – https://plotly.com/javascript/
Signature of Student:






Slide 1: Introduction
AI-Powered Business Intelligence Platform

A web application for uploading and exploring structured datasets.
Accepts CSV, Excel, and ZIP files.
Profiles columns, detects data types, and reports data-quality information.
Processes uploaded data and presents generated KPIs and charts in a dashboard.
Includes filters, AI-assisted questions, saved dataset history, and PDF reporting.


Speaker notes:
“Our project combines data upload, preparation, and analysis in one application. A user uploads a dataset, and the platform processes it and provides a dashboard to help explore the data.”

Slide 2: Literature Review
Concepts considered

ETL: Data is extracted, transformed, and loaded into a database before analysis.
Data profiling: Examining columns, types, missing values, and possible relationships helps users understand unfamiliar datasets.
Business intelligence dashboards: KPI cards and charts help summarize data for interactive exploration.


Natural-language database querying: Text-to-SQL systems aim to translate a user’s question into a database query. Schema context and query validation are important for producing useful, controlled results.
How our project applies these concepts

Combines file upload, data profiling, cleaning, database loading, and analytics in one workflow.
Uses generated KPIs, charts, and data-quality information to help users explore uploaded datasets.


Provides AI-assisted questions using the dataset schema and validates generated queries as read-only before execution.
Speaker notes:
“We based the project on established ideas from ETL, data profiling, dashboards, and natural-language database querying. Our work combines them in one prototype application.”

Slide 3: System Analysis
Problem
Understanding an unfamiliar dataset can require several manual steps.
Users may need to inspect data, clean it, prepare database tables, and build charts using separate tools.
Writing database queries can be difficult for users who do not know SQL.
Proposed system
Upload structured files through a web interface.
Profile and clean the uploaded data.
Store processed data and session metadata in a database.
Generate KPI results and chart configurations for a dashboard.
Provide filtering, dataset history, and PDF report export.
Let users ask natural-language questions about their data.

Scope and limitations
Relationship detection depends on whether the uploaded data contains suitable fields.
AI responses depend on the available schema, data, and AI service response.
Public share links now show a named, read-only dashboard with KPI values, saved insights, and generated charts. They do not expose raw table rows or provide the private dashboard's filters and editing controls.
Speaker notes:
“The application automates the initial preparation and analysis workflow. A public link now opens a read-only dashboard with KPIs, saved insights, and aggregate charts; private filtering and editing remain in the main application.”

Slide 4: System Architecture
Use this prompt to generate the architecture image:

Create a high-quality, accurate 16:9 system-architecture diagram for a college software project titled “AI-Powered Business Intelligence Platform.” Make it appropriate for a university presentation: professional, readable at slide size, clearly grouped components, consistent arrows, precise labels, and a restrained teal and indigo accent palette on a light background. Avoid decorative effects that reduce legibility. Do not include a technology-stack section.

Organize the diagram into four clearly labeled layers:
1. User Interface
Show a user accessing a web application. Label the implemented areas: Upload Data, Executive Dashboard, Data X-Ray, AI Chat, Dataset History, Profile, and Read-only Shared View. Show the user uploading CSV, Excel, or ZIP files, exploring dashboard results, inspecting data quality, and asking questions.

2. Backend API
Show the web application communicating with a backend API. Label the API responsibilities: upload and ETL, schema and status, KPIs and analytics, charts and filters, comparisons, AI chat, authentication and profile, notifications, PDF reports, and workspace sharing. Show
authenticated routes checking the bearer token. Show public share access as read-only and validated using an expiring share token. Return only the dashboard title, KPI values, saved insights, and generated chart aggregates. Omit scatter, histogram, and box charts that can expose sampled individual values. Never expose raw table rows or private account details.

3. Data Processing and Storage
Show the main processing flow with numbered arrows:

File Upload → Schema Profiling and Type Detection → Quality Analysis and Conditional Relationship Detection → Extraction → Cleaning and Standardization → Database Loading → KPI and Chart Configuration

Show a relational database storing uploaded data tables and application metadata: upload sessions, schema profiles, quality reports, detected
relationships, KPI results, chart configurations, AI insights, user accounts, and share-token records. Note that relationship detection is conditional; do not imply every dataset contains relationships.

4. AI and Reporting
Show the AI question flow:

User Question → Schema Context → AI-generated SQL → Read-only Query Validation → Database Query → Result and Explanation → Frontend

Also show saved KPI and chart information being used to generate chart insights and an executive summary. Show PDF report generation using analytics data and returning a downloadable report.
Draw clear arrow directions. Do not show AI making database writes or bypassing query validation. Do not show model training, machine learning, email delivery, Redis, S3, or other optional infrastructure. Do not show public users accessing raw database tables or private account data. Use concise labels, accurate spelling, and enough whitespace to make the complete diagram understandable in a presentation.

Slide 5: Current Progress
Implemented features
Upload workflow for CSV, Excel, and ZIP files.
Schema profiling, data-type detection, quality reporting, and conditional relationship detection.
Data cleaning and loading into database tables.
KPI generation, dashboard charts, date/category filters, and KPI comparisons.
Data X-Ray for table and field inspection, including quality information and sample values.
AI chat for questions about a dataset, with read-only SQL validation.
Saved dataset history with editable dataset names.
Account registration and sign-in, profile display-name editing, and dashboard preferences.
PDF report generation.
Public share links that provide a named, read-only view with KPI values, saved insights, and generated dashboard charts.
Verification and remaining work
The latest full backend test run recorded 61 passing tests.
Frontend TypeScript validation and production build passed in the last recorded checks.
Earlier upload testing showed database compatibility issues affecting notification persistence and one generated analytical view; these need correction and retesting.
Shared dashboards do not include private dashboard filters or editing controls. Share-link revocation and configurable expiry remain future improvements.

Speaker notes:
“The main upload, analytics, and AI workflows are implemented. Testing has also identified a few areas for follow-up, which we have kept separate from completed features.”

Slide 6: Conclusion and Future Scope
Conclusion
The project brings structured data upload, preparation, and dashboard-based analysis into one web application.
It helps users inspect dataset structure and quality, review KPIs and charts, and ask questions using natural language.
The implemented workflows have been validated with automated backend tests and frontend build checks.

Future scope
Resolve and retest the notification and analytical-view database issues.
Add share-link revocation controls and configurable expiry while preserving read-only access.
Improve AI answer quality, including clearer explanations and follow-up questions.
Conduct broader end-to-end testing with different datasets and deployment configurations.
Improve performance and error reporting for larger uploads.
Speaker notes:
“Our next steps focus on reliability, safer share-link management, and improving the AI question-answering experience.”

Slide 7: References
Kimball, R., and Ross, M. The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling, 3rd ed., Wiley, 2013.
Few, S. Information Dashboard Design: Displaying Data for At-a-Glance Monitoring, 2nd ed., Analytics Press, 2013.
Yu, T. et al. “Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task.” Proceedings of EMNLP, 2018.
Wang, B. et al. “RAT-SQL: Relation-Aware Schema Encoding and Linking for Text-to-SQL Parsers.” Proceedings of ACL, 2020.
FastAPI Documentation — https://fastapi.tiangolo.com/
PostgreSQL Documentation — https://www.postgresql.org/docs/
Pandas Documentation — https://pandas.pydata.org/docs/
React Documentation — https://react.dev/