# AI-Powered Business Intelligence Platform
## Final Project Report Content

> **Preparation note — remove before submission:** This file begins after the Cover Page, Certificate, and Candidate Declaration, which the students have prepared separately. The reference DOCX uses A4 pages with margins of approximately 2.36 cm top, 2.22 cm bottom, 2.00 cm left, and 1.50 cm right; follow the supplied department template for fonts, spacing, and page numbering. Update the table-of-contents page numbers after transferring the content into that template. Replace the figure and screenshot prompts with actual diagrams and screenshots. The Review 2 deck contains a profile image with an email address and a public-share image with a bearer token in the address bar; do not insert those screenshots without redacting the sensitive information. The screenshots show demo data and should not be labelled as Olist results.

**Project title:** AI-Powered Business Intelligence Platform  
**Application name:** AIBI Nexus  
**Course:** CSE403: Project V  
**Semester:** VII  
**Students:** Rahul Raman (23DCS106); Bhavin Rathod (23DCS110)  
**Internal Guide:** Prof. Bhavika Patel  
**Department:** Computer Science and Engineering, DEPSTAR, CHARUSAT

---

# Table of Contents

Abstract
CHAPTER 1: INTRODUCTION
   1.1 Background
   1.2 Problem Statement
   1.3 Aim and Objectives
   1.4 Scope
   1.5 Development Approach
   1.6 Organization of the Report
CHAPTER 2: LITERATURE REVIEW
   2.1 Business Intelligence and Analytical Processing
   2.2 Data Quality and Preparation
   2.3 Natural-Language Interfaces to Databases
   2.4 Research Gap and Project Position
CHAPTER 3: SYSTEM ANALYSIS
   3.1 Existing Workflow and Identified Need
   3.2 Proposed System
   3.3 Functional Requirements
   3.4 Non-Functional Requirements
   3.5 Users and Use Cases
   3.6 Feasibility and Constraints
CHAPTER 4: TECHNOLOGY STACK
   4.1 Backend and Data Processing
   4.2 Frontend
   4.3 Artificial Intelligence and Machine Learning
   4.4 Reporting and Supporting Services
   4.5 Stack Rationale
CHAPTER 5: SYSTEM DESIGN AND ARCHITECTURE
   5.1 Architecture Overview
   5.2 End-to-End Data Flow
   5.3 Schema Profiling and Type Detection
   5.4 Relationship Detection
   5.5 Data Cleaning and Quality Analysis
   5.6 Database Design
   5.7 Analytics and Visualization
   5.8 Natural-Language Analytics
   5.9 Authentication and Sharing
   5.10 Frontend Modules and API Design
CHAPTER 6: IMPLEMENTATION
   6.1 Backend Application and API Routing
   6.2 File Upload and ETL Execution
   6.3 Schema and Data Persistence
   6.4 Analytics, Chat, and Report Generation
   6.5 Frontend Implementation
   6.6 Runtime Controls and Supporting ML Utilities
CHAPTER 7: TESTING
   7.1 Test Strategy
   7.2 Test Cases
   7.3 Recorded Test Evidence
CHAPTER 8: RESULTS
   8.1 Demonstrated User Workflows
   8.2 Dashboard and Analytics Output
   8.3 AI Chat and Report Output
   8.4 Interpretation of Results
CHAPTER 9: CHALLENGES FACED
CHAPTER 10: CONCLUSION AND FUTURE SCOPE
   10.1 Conclusion
   10.2 Future Scope
11. References
12. Appendices

---

# Abstract

Organizations often store business information in spreadsheets and separate data files. Before decision-makers can use that information, someone must understand the column meanings, identify relationships, check missing or inconsistent values, prepare summaries, and build visual reports. These tasks can require technical knowledge and repeated manual effort. The AI-Powered Business Intelligence Platform, presented as AIBI Nexus, was developed as an integrated application that brings several of these activities into one browser-based workflow.

The platform accepts structured CSV and Excel files, including supported files packaged in a ZIP archive. A Python backend profiles uploaded tables, assigns semantic types to columns, checks common data-quality signals, and searches for likely relationships between tables. The ETL pipeline then cleans the data and loads session-specific tables into PostgreSQL. The analytics layer calculates business indicators, selects chart configurations, supports date and category filters, and compares selected periods. A React and TypeScript frontend presents the upload, dashboard, Data X-Ray, chat, profile, and dataset-history workflows. A natural-language assistant uses the available schema to request SQL from a hosted language model. The application validates generated statements as read-only SELECT queries before executing them and can explain returned results. Users can also create PDF report snapshots and read-only public dashboard links.

The implementation combines FastAPI, SQLAlchemy, PostgreSQL, Pandas, NumPy, React, TypeScript, Plotly, and the Groq API using the open-weight model identifier openai/gpt-oss-120b. Separate backend training routines are available for churn classification, monthly revenue forecasting, and RFM-based customer segmentation; these routines accept prepared CSV data and are not part of the main dashboard workflow shown in the review screenshots.

The submitted review presentation provides visual evidence of the upload, schema inspection, dashboard, AI chat, and PDF report flows. It contains demo data snapshots rather than a controlled performance benchmark. Weekly Report 12 records that 65 backend tests passed and that frontend type validation and a Vercel-targeted build succeeded on 5 October 2026. Those results are historical records, not a new test run for this report. The project demonstrates how data preparation, analytics, visualization, and natural-language querying can be connected in one application. Future work can strengthen the business-specific value through evidence-linked recommendations and a more complete, user-facing scenario-analysis workflow.

**Keywords:** Business Intelligence, ETL, data profiling, data quality, KPI, natural-language-to-SQL, dashboard, PostgreSQL.

---

# CHAPTER 1: INTRODUCTION

## 1.1 Background

Business Intelligence (BI) refers to the collection of processes and tools used to convert operational data into information that supports planning and decision-making. A typical analytical workflow brings data together, prepares it, organizes it for querying, and presents results through summaries, reports, and visualizations. Data warehousing and online analytical processing (OLAP) research describes this separation between routine transaction processing and analysis, and emphasizes extraction, cleaning, loading, metadata, and query tools as connected parts of an analytical environment [1].

In small teams and academic prototypes, the source material is often a set of CSV or Excel files instead of a managed warehouse. The files may have different naming conventions, date formats, missing-value markers, and table relationships. Before analysis can begin, a user may need to inspect each file, determine which columns represent dates or amounts, write joins, calculate metrics, and create charts. The work is repetitive and is more difficult for users who do not routinely write SQL or data-processing code.

Recent natural-language interfaces make it possible to ask questions about structured data in ordinary language. For such an interface to be useful, however, it must be grounded in the actual database schema and its answers should be checked against executable data queries. A natural-language response alone does not replace the preparation, validation, and visualization steps needed for a reliable BI workflow. AIBI Nexus therefore combines a natural-language assistant with conventional data-processing and analytics components.

## 1.2 Problem Statement
The Under Statement 
The project addresses the difficulty of turning several user-supplied structured files into a consistent, inspectable, and queryable analytical workspace. The main problems considered are:

1. Column names and stored values do not always reveal their business meaning directly.
2. Relationships between separate files may be undocumented.
3. Missing values, duplicate records, inconsistent categories, mixed types, and extreme numeric values can affect analysis.
4. Basic KPI and chart preparation may require SQL or spreadsheet expertise.
5. Users may have questions that are easier to express in business language than as SQL.
6. Results need to be available in a reusable dashboard or report format.

The project implements an application workflow to reduce these manual steps for supported structured files. It does not claim that every arbitrary business question can be answered correctly or that automatic schema and relationship inference is certain for every dataset.

## 1.3 Aim and Objectives

**Aim:** To design and implement a web-based business intelligence prototype that accepts structured business data, profiles and prepares it, generates analytical outputs, and supports natural-language exploration.

**Objectives:**

1. Provide a browser interface for uploading CSV, XLSX, XLS, and ZIP inputs.
2. Detect common semantic column types such as identifiers, dates, monetary values, numeric measures, categories, text, and booleans.
3. Profile uploaded tables and report selected quality indicators.
4. Infer candidate relationships between tables using column-name and value-overlap signals.
5. Apply repeatable data-cleaning rules and load session-specific data into PostgreSQL.
6. Calculate useful KPIs and generate chart configurations from the detected schema.
7. Provide dashboard filters, period comparison, and chart-level insight text.
8. Allow a user to ask questions in natural language and return results from validated read-only SQL.
9. Support PDF report generation, session history, account settings, notifications, and controlled read-only sharing.
10. Keep future enhancements distinct from capabilities visible in the current review evidence.

## 1.4 Scope

The implemented ingestion flow supports CSV, XLSX, XLS, and ZIP uploads, with a 25 MiB limit applied to each uploaded file at the API boundary. Excel profiling reads the first worksheet. ZIP processing reads supported files at the top level and ignores hidden files and macOS metadata entries. The profiler creates session-specific table names and stores analytical data in PostgreSQL.

The reviewed interface includes sign-in and sign-up screens, upload, dashboard, Data X-Ray, AI chat, dataset history, profile/settings, and a public read-only dashboard route. The backend also exposes endpoints for KPI comparison, what-if percentage adjustments, notifications, PDF output, scheduled report setup, and model training. Some of these backend capabilities do not have a complete dedicated frontend workflow in the reviewed interface.

The project does not include evidence of a live connector to a production CRM, ERP, or streaming source. The supplied repository contains Olist data files for development; the Review 2 presentation also shows a separate synthetic SaaS-style demo. Results from those two data contexts must not be combined. Churn, forecasting, and segmentation routines accept prepared CSV features, but the reviewed screenshots do not demonstrate predictions from those models in the main dashboard.

## 1.5 Development Approach

The implementation follows a modular approach:

1. Define the user workflow and system components.
2. Create schema detection, relationship detection, quality profiling, and ETL modules.
3. Store platform metadata and uploaded analytical data in PostgreSQL.
4. Add backend routes for upload, analytics, chat, authentication, and reporting.
5. Build the React frontend around these routes.
6. Add tests around data processing, analytics, SQL validation, authentication, and operational behavior.
7. Review the running interface and record incremental weekly progress.

The weekly records describe this development as a sequence from project planning and schema design through ETL, analytics, frontend integration, authentication, Data X-Ray, sharing, and hardening.

## 1.6 Organization of the Report

Chapter 2 reviews BI, data quality, and text-to-SQL research. Chapter 3 analyzes the system requirements and scope. Chapter 4 explains the selected technologies. Chapter 5 presents the system design and architecture. Chapter 6 describes how the design is implemented across the API, ETL, analytics, AI, reporting, and frontend modules. Chapter 7 records the testing strategy and dated evidence. Chapter 8 presents the demonstrated results. Chapter 9 discusses challenges encountered. Chapter 10 concludes the report and proposes future scope. References and appendices follow.

---

# CHAPTER 2: LITERATURE REVIEW

## 2.1 Business Intelligence and Analytical Processing

Chaudhuri and Dayal describe data warehousing and OLAP as connected parts of decision support, including data extraction, cleaning, loading, metadata, and analytical queries [1]. AIBI Nexus follows a smaller version of this workflow: it accepts structured files, profiles and cleans their contents, stores session tables in PostgreSQL, and presents selected measures through a dashboard and report. Traditional BI commonly starts from a prepared schema. The project reduces some setup work by inferring column types and candidate relationships from uploaded data, while leaving the final interpretation to the user.

## 2.2 Data Quality and Preparation

Wang and Strong frame data quality in relation to consumers, tasks, representation, and access rather than accuracy alone [2]. The project implements a limited set of repeatable checks, including missing values, duplicates, mixed types, and extreme numeric values. Its cleaner standardizes selected fields and flags outliers instead of deleting them. The resulting score summarizes these configured rules; it does not prove that a field has the correct business meaning. A difference between calculated and persisted quality details is discussed in Chapter 9.

## 2.3 Natural-Language Interfaces to Databases

Text-to-SQL research examines how a system maps a natural-language question to a database query. Spider highlights the difficulty of generalizing across databases and multi-table schemas [3], while RAT-SQL studies links between question terms and schema elements [4]. AIBI Nexus uses a hosted model to propose PostgreSQL SELECT queries after supplying the current session's table and column names. A Python validator checks the generated statement before execution, and the returned rows are passed to a response-generation step. This is an application-level schema-grounded workflow; the project does not implement RAT-SQL or claim evaluation on Spider. The validator reduces some risks but cannot guarantee that a valid query reflects the user's intended business meaning.

## 2.4 Research Gap and Project Position

The reviewed work addresses analytical storage, data quality, and language-to-query mapping as related but separate problems. AIBI Nexus combines file ingestion, profiling, ETL, KPI and chart generation, chat-based queries, and report output in one academic application. Its contribution is this integration and the practical workflow around it, rather than a new language model or benchmark-validated algorithm. Review 2 feedback motivates future work on evidence-linked business recommendations and transparent scenario comparison.

---

# CHAPTER 3: SYSTEM ANALYSIS

## 3.1 Existing Workflow and Identified Need

In a manual workflow, an analyst inspects each file, infers table relationships, cleans inconsistent rows, calculates measures, and prepares charts and reports. Repeating these steps can take time and produce inconsistent formulas. The proposed application brings these activities into a guided browser workflow and exposes inferred schema and quality details for user review.

## 3.2 Proposed System

The proposed system combines a React and TypeScript client, FastAPI routes, PostgreSQL, Python data-processing modules, analytics services, and an external AI model provider. An upload creates a session; the backend profiles, cleans, and stores the files; the client then uses the session identifier to request schema, dashboard, chat, and report data. Synchronous ETL is the default path. Redis-backed queued processing and S3-compatible staging are optional configurations.

## 3.3 Functional Requirements

| ID | Requirement | Implemented behavior |
|---|---|---|
| ID | Requirement | Implemented behavior |
|---|---|---|
| FR-01 | Account access | Sign-up, sign-in, profile settings, and protected session access are available. |
| FR-02 | Upload and inspect data | CSV, Excel, and ZIP files are profiled; Data X-Ray displays schema, quality indicators, and relationships. |
| FR-03 | Prepare and store data | ETL cleans supported values, records actions, and stores tables and metadata by session. |
| FR-04 | Analyze data | The dashboard provides selected KPIs, charts, date/category filters, and period comparison. |
| FR-05 | Ask questions and export | AI chat uses session schema context; the report route generates a PDF snapshot. |
| FR-06 | Manage access and history | Users can revisit sessions, rename datasets, receive notifications, and create read-only share links. |
| FR-07 | Train supporting models | A backend route accepts prepared CSV data for churn, forecast, or segmentation training. |

## 3.4 Non-Functional Requirements

| Category | Requirement |
|---|---|
| Usability | Provide separate upload, inspection, dashboard, chat, and history screens. |
| Maintainability | Keep API, ETL, schema detection, analytics, AI, reports, and ML in modules. |
| Security | Apply authentication settings, session ownership checks, CORS controls, rate limiting, and SQL validation. |
| Reliability | Provide health/readiness routes, request logging, selected retries, and backup utilities. |
| Portability | Load database, AI, and optional service settings from environment variables. |

## 3.5 Users and Use Cases

**Account holder / analyst:** uploads files, inspects the detected schema, reviews quality signals, filters KPIs, asks questions, and exports a report.

**Business reviewer:** opens a shared dashboard and reviews aggregate KPIs, charts, and saved insights.

**Project maintainer:** configures service settings and reviews logs and health information.

**Primary use case — analyze uploaded data:**

1. The user signs in when authentication is enabled and selects supported files.
2. The server validates them, profiles their columns, and suggests relationships.
3. ETL cleans and stores the data under a new upload session.
4. The user reviews the schema in Data X-Ray and explores KPIs and charts.
5. The user can ask a question, download a PDF, or create a time-limited read-only link.

**Figure prompt — use-case diagram:** “Create a clean academic UML use-case diagram for an AI-powered business intelligence web application. Actors: Account Holder, Business Reviewer, and Project Maintainer. Account Holder use cases: Sign Up/Sign In, Upload CSV/Excel/ZIP, Inspect Schema and Data Quality, View Data X-Ray, View KPI Dashboard, Apply Date and Category Filters, Compare Periods, Ask AI Data Question, View Chat History, Download PDF Report, Rename Dataset, Manage Profile and Settings, Create Read-only Share Link, View Notifications. Business Reviewer: Open Shared Dashboard, View KPIs and Aggregate Charts. Project Maintainer: Configure Database and AI Provider, Monitor Health and Logs, Run Optional ETL Worker. Use standard UML use-case notation and group application capabilities inside a system boundary labelled AIBI Nexus. Do not add unsupported features such as live database connectors or interactive ML predictions.”

## 3.6 Feasibility and Constraints

The project uses widely available Python, TypeScript, and PostgreSQL tooling. AI chat depends on configured provider access; queued ETL requires Redis, and distributed staging requires S3-compatible storage. The supported formats, per-file upload limit, in-memory profiling, and heuristic relationship detection define the practical scope. The system is intended for structured tabular data, and inferred relationships and metrics should be checked when business definitions are ambiguous.

---

# CHAPTER 4: TECHNOLOGY STACK

| Layer | Technology | Role in the project |
|---|---|---|
| Programming language | Python 3.11 (as specified in the project setup documentation) | API, profiling, ETL, analytics, AI integration, reporting, and model training. |
| API framework | FastAPI | REST endpoints for uploads, schema, analytics, authentication, chat, reports, sharing, and model training. |
| Validation and ORM/database access | Pydantic and SQLAlchemy | Request/response validation and PostgreSQL connectivity/query execution. |
| Relational database | PostgreSQL | Platform metadata, authentication/session records, and dynamic tables for uploaded datasets. |
| Data processing | Pandas and NumPy | Reading, profiling, transforming, aggregating, and cleaning tabular values. |
| File support | OpenPyXL, chardet, python-dateutil, python-multipart | Excel reading, CSV encoding detection, flexible date parsing, and multipart uploads. |
| Frontend language and UI | React 19 and TypeScript | Browser-based pages and typed API contracts. |
| Frontend framework/build | TanStack Start/Router, Vite, Tailwind CSS | Routing, application rendering, development server, and styling. |
| Frontend data and charts | TanStack Query, Axios, Plotly | API state and requests, interactive charts, and dashboard data rendering. |
| AI service | Groq API with model identifier openai/gpt-oss-120b | Schema-aware SQL generation, answer explanation, chart insights, and executive summaries. |
| ML components | XGBoost, scikit-learn, Prophet, joblib | Prepared-CSV training for churn, revenue forecasting, and RFM segmentation. |
| PDF output | ReportLab | Builds in-memory dashboard report PDFs. |
| Optional operations | Redis, Boto3/S3-compatible storage | Shared rate-limit state, optional asynchronous ETL queue, and optional staged file storage. |
| Automated checks | pytest, frontend TypeScript tooling | Backend unit/regression tests and frontend type/build checks. |

The active frontend implementation is React and TypeScript. A legacy dependency/comment in the Python requirements file mentions Streamlit, but the reviewed interface routes and API client are implemented in React; Streamlit is therefore not listed as the current user interface.

## 4.1 Stack Rationale

FastAPI provides typed HTTP endpoints and multipart file-upload support [5]. PostgreSQL stores both metadata and structured analytical tables and supports views and aggregate SQL [6]. Pandas supports tabular input, missing-value handling, joins, grouping, and export workflows [7]. React supports reusable interface components, while TypeScript adds static types to the client API contract [8]. SQLAlchemy provides database connectivity and SQL execution abstractions [9]. Plotly is used for the interactive chart display, and ReportLab constructs downloadable PDF reports [10], [11].

The Groq client calls the configured model identifier openai/gpt-oss-120b for chat completions [12]. The model is an external service dependency; the project does not train or fine-tune it. Model access, availability, latency, and response quality depend on the configured provider account and network.

The separate churn routine uses XGBoost's classifier API [15], the revenue routine uses Prophet's fit/forecast workflow [13], and the customer-segmentation routine uses scikit-learn KMeans [14]. These model routines train from prepared CSV input; the reviewed frontend does not show a prediction workflow for them.

---

# CHAPTER 5: SYSTEM DESIGN AND ARCHITECTURE

## 5.1 Architecture Overview

AIBI Nexus uses a client-server design. The React and TypeScript frontend sends requests to FastAPI, which coordinates authentication, profiling, ETL, analytics, chat, and reporting. PostgreSQL stores platform metadata and uploaded session data. The Groq API supplies selected language-model functions. Redis and S3-compatible storage are optional services for queued or distributed processing.

**Figure prompt — system architecture:** “Draw a layered architecture for AIBI Nexus with the React/TypeScript browser client, FastAPI route groups, Python profiling/ETL/analytics/AI/report services, PostgreSQL metadata and session tables, and the Groq API. Show Redis/worker and S3 staging as optional dashed components. Label upload, data preparation, analytics, chat, and report flows. Do not add live connectors or ML prediction screens.”

## 5.2 End-to-End Data Flow

1. The browser sends supported files to the upload route, which validates type and size.
2. Profiling reads the data, infers column types, calculates quality signals, and identifies candidate relationships.
3. ETL cleans and loads session-specific PostgreSQL tables and metadata; eligible relationships may produce SQL views.
4. Analytics prepares KPI and chart configurations. The frontend requests these alongside schema, filters, comparisons, and insights.
5. Chat uses session schema context to produce a validated query and explanation; reporting builds a filtered PDF; sharing returns a read-only view.

**Figure prompt — ETL data-flow diagram:** “Show CSV/Excel/ZIP upload, validation, profiling, cleaning, PostgreSQL session tables and metadata, relationship views, KPI/chart generation, and the dashboard, Data X-Ray, chat, PDF, and share outputs. Mark Redis worker and S3 staging as optional paths.”

## 5.3 Schema Profiling and Type Detection

The profiler reads files into Pandas DataFrames and assigns one of seven semantic types:

| Semantic type | Example meaning | Typical use |
|---|---|---|
| ID | Primary key, foreign key, code, or UUID | Counting distinct entities and detecting relationships. |
| Datetime | Date, timestamp, or time period | Trend charts, date filters, and period comparison. |
| Currency | Revenue, payment, amount, cost, or price-like values | Monetary KPIs and numeric aggregation. |
| Numeric | Quantity, age, score, or other numeric measure | Aggregation, distribution charts, and analytics. |
| Category | Low-cardinality grouping value | Category filters and bar/pie-style summaries. |
| Text | High-cardinality descriptive value | Inspection and natural-language context. |
| Boolean | True/false, yes/no, or binary flag | Filtering and descriptive analysis. |

It combines data types, name hints, uniqueness, value patterns, and sampled date parsing. Profiles include null and unique counts, samples, and column positions. Inferred types are suggestions and can be ambiguous; users can inspect them in Data X-Ray.

## 5.4 Relationship Detection

For multi-file uploads, the detector compares ID-like columns using normalized names and value overlap. Candidate links receive high, medium, or low confidence; low-confidence links are skipped when join views are created. Name and value matches do not establish business meaning or join cardinality, so users should review proposed links.

**Figure prompt — entity relationship diagram:** “Draw the fixed metadata tables upload_sessions, uploaded_files, schema_profiles, detected_relationships, quality_reports, kpi_results, chart_configs, and ai_insights, showing documented session_id and chart_id links. Show account, notification, sharing, and schedule tables as runtime records, and depict uploaded data as dynamic session-prefixed tables/views. Do not invent foreign keys or unspecified columns.”

## 5.5 Data Cleaning and Quality Analysis

The cleaner converts common null markers, coerces mixed numeric values, removes duplicates, treats missing identifiers where needed, imputes selected values by type, normalizes dates/categories, and flags outliers using a three-IQR boundary. It records its actions and does not automatically delete flagged outliers. The quality reporter checks missingness, duplicates, outliers, and conflicts between inferred and observed types, then produces issue descriptions and a rule-based score.

**Data-quality interpretation:** This score summarizes implemented checks; it is not a certification. Some calculated quality fields are not consistently persisted by the loader, so screenshot values are treated as displayed observations rather than audited measurements.

## 5.6 Database Design

The platform stores session and analytics metadata in fixed tables:

| Table | Purpose |
|---|---|
| Table group | Purpose |
|---|---|
| upload_sessions, uploaded_files | Session ownership/status and source-file details. |
| schema_profiles, detected_relationships, quality_reports | Detected columns, candidate joins, and quality summaries. |
| kpi_results, chart_configs, ai_insights | Saved KPI, chart, and insight/chat metadata. |
| Account and workspace records | Authentication sessions, notifications, shares, and report schedules. |

Cleaned business data is stored in dynamic PostgreSQL tables named with a shortened session prefix and normalized file name. Eligible joins and analytical views may also be created. Runtime records should not be interpreted as having foreign-key constraints unless declared in the schema.

## 5.7 Analytics and Visualization

The KPI engine uses semantic profiles and name hints to select measures and identifiers. Depending on available fields, it can calculate revenue, order and customer counts, average order value, maximum transaction, revenue per customer, and other selected indicators. It uses distinct order counts for average order value when suitable identifiers exist. Chart selection uses detected types and relationships; Plotly renders chart data in the frontend. Date and category filters are checked against the session schema, and comparison can use the immediately preceding date interval. A what-if endpoint applies percentage changes as arithmetic projections, not causal forecasts.

## 5.8 Natural-Language Analytics

The chat route supplies the session's table/column context with the user's question and requests a PostgreSQL SELECT. It validates the returned SQL, executes accepted queries, and sends result rows to an explanation step. The validator rejects non-SELECT statements, comments, multiple statements, and selected mutation keywords; the prompt also asks for a bounded result. This is application-level checking, not formal proof that every query is safe or semantically correct.

## 5.9 Authentication and Sharing

Account records and bearer sessions are stored in PostgreSQL; passwords are hashed with a salted PBKDF2 derivation. Production-like environments require authentication, and protected session routes check ownership. Sharing generates a random token, stores its SHA-256 hash, and expires the link after seven days. The public endpoint serves selected KPIs, insights, and whitelisted chart types in read-only form; an unexpired link grants access to that dashboard data.

## 5.10 Frontend Modules and API Design

File-based routes and a shared Axios API client support upload, dashboard, Data X-Ray, chat, sessions, profile settings, and a token-based shared dashboard. Backend route groups cover uploads, schema, analytics, comparisons, chat, authentication, notifications, reporting, ML, and workspace functions. Health, readiness, and metrics routes provide operational information.

**Figure prompt — sequence diagram:** “Show a user uploading files through React to FastAPI, followed by validation, profiling, ETL, PostgreSQL persistence, and KPI/chart preparation. Then show the frontend requesting schema and analytics and rendering the dashboard. Include Redis/worker only as an optional dashed path.”

---

# CHAPTER 6: IMPLEMENTATION

The implementation is organized into backend modules, shared data-processing services, a PostgreSQL storage layer, and a browser-based frontend. This organization lets the upload workflow share schema profiles with analytics, chat, and reporting while keeping those functions in separate modules. The main source directories are `api/`, `schema_detection/`, `etl/`, `analytics/`, `ai/`, `reports/`, `ml/`, and `frontend/src/`.

| Implementation area | Main project location | Responsibility |
|---|---|---|
| API application and route groups | `api/` | Starts FastAPI, applies middleware, and exposes upload, schema, analytics, chat, authentication, reporting, and workspace routes. |
| Schema profiling | `schema_detection/` | Reads table structures, assigns semantic types, identifies candidate relationships, and creates data-quality summaries. |
| Extract, transform, load | `etl/` | Reads uploaded data, applies cleaning rules, loads session tables and metadata, and creates eligible join views. |
| Analytics and filters | `analytics/` | Calculates KPIs, comparison periods, chart configurations, and chart data using session profiles and filters. |
| AI services | `ai/` | Builds schema-aware SQL prompts, validates generated queries, explains query results, and creates insight text. |
| PDF and ML utilities | `reports/`, `ml/` | Builds downloadable report snapshots and provides separate model-training routines for prepared CSV files. |
| User interface | `frontend/src/` | Implements file-based pages for upload, dashboard, Data X-Ray, chat, sessions, account settings, and public sharing. |

## 6.1 Backend Application and API Routing

The backend entry point, `api/main.py`, creates the FastAPI application, registers middleware for rate limiting, request logging, and metrics, and mounts route groups under `/api`. It exposes health, readiness, and metrics endpoints and checks PostgreSQL during startup. Separate routers handle uploads, schema, analytics, chat, authentication, reporting, and workspace functions. The browser sends files as multipart form data and uses a returned session identifier for later requests; routes delegate processing to the corresponding service modules.

## 6.2 File Upload and ETL Execution

The upload route accepts CSV, XLSX, XLS, and ZIP files, checks the 25 MiB per-file limit, creates a UUID session, and records upload metadata. By default it runs ETL synchronously and retries once for selected transient failures. The response includes status, row/table totals, views, errors, and schema summary. With `ETL_ASYNC` enabled, files are staged, queued, and processed by a worker; Redis and S3-compatible storage are optional for this path.

The pipeline extracts files, profiles their tables, cleans DataFrames, loads session-prefixed PostgreSQL tables, and builds eligible views. CSV parsing uses encoding detection and fallback options; Excel profiling uses the first worksheet, and ZIP processing selects supported tabular files. Cleaning actions are recorded for missing values, duplicates, type normalization, and outlier flags.

## 6.3 Schema and Data Persistence

Profiles, relationship confidence, and selected quality summaries are stored alongside session and analytics metadata. The same detected schema informs Data X-Ray, KPI selection, and chat context. Cleaned business rows remain in session-specific data tables, with eligible join views available for cross-table analysis. The quality persistence caveat in Section 5.5 applies when reading stored summary values.

## 6.4 Analytics, Chat, and Report Generation

Analytics routes produce KPI and chart results, apply date/category filters, and support period comparisons. A percentage-based what-if endpoint calculates arithmetic projections. Chat sends the selected session's schema and question to the configured model, validates generated SQL, and summarizes returned rows. The report route builds an in-memory PDF from session details, KPIs, quality summaries, and chart analysis. Sharing stores a token hash and returns selected dashboard data in read-only form.

## 6.5 Frontend Implementation

The React and TypeScript frontend has file-based routes for account access, upload, dashboard, Data X-Ray, chat, sessions, profile settings, and token-based sharing. A shared API client attaches bearer tokens to protected requests. Reusable components render forms, tables, filters, cards, and Plotly charts. The review screenshots provide evidence for several routes and are described as demo snapshots in Chapter 8.

## 6.6 Runtime Controls and Supporting ML Utilities

Environment variables configure database and AI access, authentication, CORS, rate limits, and optional ETL/storage services. Production-like settings require trusted browser origins; request logging includes a correlation identifier. Separate training routes accept prepared CSV files for churn classification, revenue forecasting, and RFM segmentation. These are backend utilities and are not shown as dashboard predictions in the review screenshots.

**Figure prompt — implementation module diagram:** “Create an academic implementation diagram using only these project modules: React/TypeScript file-based frontend; FastAPI application and route groups; schema_detection; ETL extraction, cleaning, loading, and optional job worker; analytics; AI SQL/insight services; PDF reporting; machine-learning training routes; PostgreSQL; Groq API; optional Redis and S3-compatible storage. Show the normal upload-to-dashboard path with arrows and mark Redis/worker and S3 as optional configuration paths. Do not add deployment infrastructure, live business-system connectors, or a prediction interface that is not shown in the review presentation.”

---

# CHAPTER 7: TESTING

## 7.1 Test Strategy

The repository contains backend tests organized around schema detection, ETL, storage, filters, KPI calculation/comparison, AI SQL safety, authentication, rate limiting, metrics, health checks, notifications, model routes, backup helpers, and production configuration. The intended test levels are:

1. **Unit testing:** verify individual helpers and calculation rules such as semantic type detection, cleaning, filter validation, KPI formulas, scenario arithmetic, and SQL validation.
2. **API testing:** verify route registration, request validation, authentication behavior, session access, upload errors, and response shapes.
3. **Integration testing:** exercise database-backed upload, analytics, chat history, report generation, notification, and sharing behavior.
4. **Frontend checks:** run TypeScript validation and a production-targeted build.
5. **Manual workflow review:** upload a supported file, inspect the profile, view a dashboard, ask a question, and export or share a report.

## 7.2 Test Cases

| Test ID | Scenario | Expected result |
|---|---|---|
| TC-01 | Upload a valid CSV file | A session is created, profiling begins, and the API returns a session identifier and schema summary. |
| TC-02 | Upload a supported Excel or ZIP file | The first Excel sheet or supported archive contents are parsed into one or more profiled tables. |
| TC-03 | Upload an unsupported extension or oversized file | The API rejects the request with a client error and a clear validation message. |
| TC-04 | Detect numeric strings, date strings, booleans, and currency-like columns | Columns receive one of the supported semantic types and profile statistics are returned. |
| TC-05 | Profile files with candidate ID relationships | Candidate pairs are assigned confidence and match statistics; low-confidence links are not used to create join views. |
| TC-06 | Clean null markers, duplicates, mixed values, and extreme numeric values | The cleaner records actions, applies type-based handling, and flags outliers rather than deleting them. |
| TC-07 | Calculate KPIs where an order identifier and revenue field exist | KPI outputs use distinct order counts for order-level measures and do not infer revenue from an arbitrary price field. |
| TC-08 | Generate a dashboard with valid date/category filters | KPI and chart queries use validated filters and return chart data for display. |
| TC-09 | Submit safe SELECT and unsafe SQL to the SQL validator | A single permitted SELECT is accepted; mutation and multi-statement queries are rejected. |
| TC-10 | Access another account's session | Ownership enforcement prevents access and does not reveal the other user's data. |
| TC-11 | Generate a PDF report for a known session | A PDF is returned with session scope, KPI, uploaded-file, quality, chart, and insight sections where data exists. |
| TC-12 | Open a public share link | A valid link displays a read-only dashboard with selected aggregate chart types; expired or invalid tokens should be rejected. |
| TC-13 | Run the frontend type check and production build | TypeScript and the configured production build complete without errors. |

This table is a repeatable test plan based on the implementation and test modules. It should not be read as evidence that every case was run in the same test session. The recorded status below is limited to dated evidence in the project materials.

## 7.3 Recorded Test Evidence

Weekly Report 12, covering 29 September to 5 October 2026, records **65 backend tests passed**, with frontend type validation and a Vercel-targeted production build also reported as successful. The same report records production-mode sign-up/sign-in, protected API access, profile access, and authenticated session access as tested. Earlier weekly records describe successful sample CSV upload, ETL, dashboard, filters, chat history, PDF export, and local frontend/backend connectivity checks.

The review presentation shows screenshots of the application flows, including upload, Data X-Ray, dashboard, chat, and PDF output. These are evidence of displayed behavior during the review, not a benchmark of model accuracy, scalability, or production availability. The report uses the dated weekly record as the test result and does not present it as a new test run.

---

# CHAPTER 8: RESULTS

## 8.1 Demonstrated User Workflows

The Review 2 presentation provides a set of visual snapshots of the application. The deck includes more than one demo dataset context, so the values below are described as screen observations and should not be combined into a single dataset result.

| Demonstrated screen | Observation visible in the presentation |
|---|---|
| Sign-in and sign-up | Account entry screens are present in the React interface. |
| Upload | The page accepts CSV, XLSX, XLS, and ZIP and displays selected files before submission. |
| Upload result | A SaaS-style example shows a table named saas_users.csv with 200 rows and 5 columns, field types, null/unique information, and candidate relationships to other demo tables. |
| Data X-Ray | A separate snapshot displays 4 tables, 22 fields, 1,000 rows, table quality cards, column examples, and relationship information. |
| Dashboard | KPI cards, date/category controls, executive-summary text, charts, and chart-specific insights are visible. |
| AI Chat | A natural-language prompt returns an explanation about a demo dataset, including a note about quality or limitations. |
| PDF report | A two-page report preview includes executive-report text, KPI values, uploaded-data details, a data-quality table, and chart analysis. |
| Shared dashboard | The deck contains a public, read-only shared view. Use a sanitized screenshot if it is included in the report. |

## 8.2 Dashboard and Analytics Output

One dashboard screenshot visibly displays example values including Total Revenue of approximately 45.5K, Total Orders of 500, Total Customers of 200, Average Order Value of 91.09, Maximum Transaction of 199.99, Revenue per Customer of 260.40, and a data time span of 232 days. These values are presented as what appeared in the review screenshot. The filter state and exact source-file contents are not fully recorded in the deck, so the values should not be interpreted as a reproducible benchmark or reconciled across separate screenshots.

The dashboard demonstrates that schema metadata can be used to populate KPI cards and chart configurations. The Data X-Ray screen demonstrates field-level inspection, including type and quality summaries. Because the ETL metadata loader currently applies defaults to some persisted quality fields, the 100% quality value visible in one screenshot should be described as a displayed demo value rather than independent proof that the complete quality calculation is accurate.

## 8.3 AI Chat and Report Output

The review deck shows an AI chat answer based on a demo dataset and a separate generated PDF report. These screens demonstrate the user flow from a business-language question to an explanation and from a session dashboard to a document-style summary. They do not establish accuracy for all questions or datasets. The SQL generation component uses exact-schema prompt context and a read-only validator, while the answer remains dependent on provider output and the correctness of the selected query.

## 8.4 Interpretation of Results

The implementation demonstrates the connection of several BI tasks in one workflow: file ingestion, schema inspection, cleaning, PostgreSQL storage, KPI and chart generation, AI-assisted querying, and report output. The most visible result is the integrated user journey. No performance benchmark, model-accuracy metric for chat, deployment uptime measure, or comparative business-impact study is claimed in this report.

**Screenshot placement prompts:**

1. **Figure 8.1 — Upload and schema result:** Insert the upload page and its SaaS-style demo result. Caption the dataset context; do not label it as Olist data.
2. **Figure 8.2 — Data X-Ray:** Insert the table, field, quality, and relationship view. Identify displayed quality values as demo-screen values.
3. **Figure 8.3 — Dashboard:** Insert the KPI cards, filters, and charts. State that the values come from the presentation snapshot.
4. **Figure 8.4 — AI chat and PDF:** Insert the sample question/answer and report preview. Crop or redact personal details and any bearer token before use.
5. **Figure prompt — results workflow:** “Create an academic diagram of the demonstrated AIBI Nexus flow: upload a structured demo dataset, inspect inferred schema, review KPI cards/charts, ask a data question, and export a PDF. Use no invented accuracy or performance values.”

---

# CHAPTER 9: CHALLENGES FACED

## 9.1 Heterogeneous File Schemas

Files from different sources use inconsistent column names, data types, date formats, and missing-value markers. CSV encoding can also vary, while Excel files may contain multiple worksheets. The implementation handles common encodings and uses the first worksheet, but semantic type detection still depends on observed values and naming hints. A field called amount, value, or status may need business context before its meaning is clear. This is why the profile and samples are shown for user inspection.

## 9.2 Relationship Inference

Finding likely joins without declared keys requires balancing useful matches against false matches. Name similarity and value overlap provide evidence, but do not verify business meaning, uniqueness, or one-to-many versus many-to-many behavior. The detector assigns confidence levels and low-confidence links are excluded from view creation. Even a high-confidence candidate still needs review when identifiers are reused or values are transformed across files.

## 9.3 Data Quality Consistency

The profiler computes detailed quality information in memory, while the loader currently persists defaults for some summary fields instead of passing through the full report consistently. This can make the saved score differ from the calculated profile and can affect what appears later in Data X-Ray or a PDF. The report distinguishes the displayed sample value from a fully reconciled quality result. A clear next improvement is to persist one authoritative quality payload and test that the same values appear in the schema response, dashboard, and report.

## 9.4 KPI Meaning and Table Grain

The same numeric field can represent unit price, total transaction value, cost, or revenue. Summing at the wrong table grain can double count values, especially when a table contains multiple item rows per order. The KPI engine uses semantic and name hints, excludes selected unsuitable measures, and uses distinct order counts for average order value when order identifiers are detected. These heuristics improve consistency, but users still need to confirm metric definitions and table grain before using a value in a business conclusion.

## 9.5 Language-Model Output

Natural-language questions can be ambiguous, and generated SQL can reference the wrong measure or answer a different interpretation of the question. The external model also depends on provider availability and credentials. Schema context, a read-only validator, and fallback responses address parts of this problem, but they cannot establish that the model chose the intended business meaning. The displayed response should therefore be reviewed against the returned values and the dashboard context, particularly before using it to justify a decision.

## 9.6 Frontend and Backend Integration

The project encountered API host, port, and CORS mismatches during local integration, as recorded in earlier weekly reports. A configurable API base URL, health/readiness endpoints, request logging, and frontend error messages were added to make these issues easier to identify. This work showed that a successful frontend build does not by itself confirm that the browser can reach the API; integration checks also need the running service, matching origin settings, and a working database connection.

## 9.7 Optional Service Configuration

The application can use PostgreSQL, the AI provider, and optionally Redis and S3-compatible storage. Each service has separate credentials and availability assumptions, and the optional worker path requires its queue and staging configuration to agree. Keeping environment variables consistent between the API and worker is important for repeatable processing. The project uses environment-based settings so secrets and service addresses do not need to be embedded in source code.

## 9.8 Evidence and Demonstration Data

The repository contains Olist development data, while the presentation also shows a synthetic SaaS-style dataset. Screenshots show different table and row totals because they represent separate examples. The report labels each result by the context visible in the deck and does not attribute the SaaS-style values to Olist. This distinction is necessary so that screenshots remain evidence of the interface and are not mistaken for a controlled, reproducible evaluation.

---

# CHAPTER 10: CONCLUSION AND FUTURE SCOPE

## 10.1 Conclusion

The AI-Powered Business Intelligence Platform brings structured-file upload, automated schema profiling, selected data-cleaning operations, PostgreSQL storage, KPI calculation, chart generation, natural-language querying, and PDF reporting into one application. Its modular organization separates the frontend, API, schema detection, ETL, analytics, AI integration, database, and reporting code. Review screenshots demonstrate the main user-facing flow, while the weekly records provide dated evidence of backend tests and frontend build checks.

The project shows how an AI service can be used as one component within a broader BI workflow. The results depend on data profiling, metric definitions, query validation, and human interpretation. The application is best presented as an academic prototype that demonstrates an integrated analytics workflow rather than as a replacement for a governed enterprise BI environment.

The evidence supports the main project objective: a user can move from structured-file upload to inspection, dashboard analysis, a natural-language query, and a report within one application. The weekly records provide dated testing evidence, while the presentation supplies interface examples. Evaluation claims are kept to those sources; further work should measure query correctness, data-quality consistency, and user experience with repeatable datasets and expected results.

## 10.2 Future Scope

The following items are proposed future work and are not represented as completed functionality in the current review evidence:

1. **Business-specific explainable recommendations:** Build on detected KPI changes to explain which dataset fields and segments support an observation, identify uncertainty, and suggest practical next steps. Each recommendation should link to the supporting query or chart so it is reviewable.
2. **A user-facing scenario workspace:** Extend the existing backend percentage-adjustment endpoint with a frontend that states assumptions, compares a scenario to a baseline, shows the affected KPIs, and distinguishes arithmetic projection from a statistically validated forecast.
3. **Root-cause exploration:** Let a user drill from a KPI into available date, category, or relationship dimensions and compare contributing groups. The system should distinguish correlation from causation.
4. **Stronger data-quality persistence:** Store the profiler's calculated quality score, issue counts, and actions consistently; show the rule and threshold behind each score and support user-defined thresholds.
5. **Interactive ML workflow:** Add validated prediction/inference screens, model evaluation summaries, feature checks, artifact versioning, and explanation of model limitations for churn and segmentation models.
6. **Data-source integrations and refresh:** Add governed connectors and refresh history for selected databases or business applications, with permission management and data-freshness indicators.
7. **Report workflow:** Provide a user-facing scheduler interface, delivery history, retry/error status, and configurable report recipients for scheduled PDF reports.
8. **Deployment and operations:** Compare suitable hosting options, document environment setup, automate repeatable deployment, and add monitoring and backup verification for the chosen operating environment.
9. **Text-to-SQL evaluation:** Create a representative test set of business questions and expected query results, measure execution correctness, and include adversarial query-safety cases.
10. **Usability and accessibility:** Test the interface with users who have different levels of data and SQL experience and improve accessibility, explanations, and error recovery based on feedback.

The Review 2 feedback specifically motivates prioritizing the first item: a grounded business-analysis workflow with traceable evidence can provide more project-specific value than a general-purpose chat box alone.

---

# 11. References

[1] S. Chaudhuri and U. Dayal, “An overview of data warehousing and OLAP technology,” *SIGMOD Record*, vol. 26, no. 1, pp. 65–74, Mar. 1997, doi: 10.1145/248603.248616. [Online]. Available: https://sigmodrecord.org/1997/03/15/an-overview-of-data-warehousing-and-olap-technology/

[2] R. Y. Wang and D. M. Strong, “Beyond accuracy: What data quality means to data consumers,” *Journal of Management Information Systems*, vol. 12, no. 4, pp. 5–33, 1996, doi: 10.1080/07421222.1996.11518099.

[3] T. Yu *et al*., “Spider: A large-scale human-labeled dataset for complex and cross-domain semantic parsing and text-to-SQL task,” in *Proc. 2018 Conf. Empirical Methods in Natural Language Processing (EMNLP)*, Brussels, Belgium, 2018, pp. 3911–3921, doi: 10.18653/v1/D18-1425. [Online]. Available: https://aclanthology.org/D18-1425/

[4] B. Wang, R. Shin, X. Liu, O. Polozov, and M. Richardson, “RAT-SQL: Relation-aware schema encoding and linking for text-to-SQL parsers,” in *Proc. 58th Annual Meeting of the Association for Computational Linguistics*, 2020, pp. 7567–7578, doi: 10.18653/v1/2020.acl-main.677. [Online]. Available: https://aclanthology.org/2020.acl-main.677/

[5] FastAPI, “Request Files.” [Online]. Available: https://fastapi.tiangolo.com/tutorial/request-files/. Accessed: Oct. 22, 2026.

[6] PostgreSQL Global Development Group, “PostgreSQL Documentation.” [Online]. Available: https://www.postgresql.org/docs/. Accessed: Oct. 22, 2026.

[7] The pandas development team, “pandas User Guide.” [Online]. Available: https://pandas.pydata.org/docs/user_guide/. Accessed: Oct. 22, 2026.

[8] Meta Open Source, “React Documentation.” [Online]. Available: https://react.dev/learn. Accessed: Oct. 22, 2026.

[9] SQLAlchemy Authors, “SQLAlchemy 2.0 Documentation.” [Online]. Available: https://docs.sqlalchemy.org/en/20/. Accessed: Oct. 22, 2026.

[10] Plotly, “Plotly JavaScript Open Source Graphing Library.” [Online]. Available: https://plotly.com/javascript/. Accessed: Oct. 22, 2026.

[11] ReportLab, “ReportLab Documentation.” [Online]. Available: https://docs.reportlab.com/. Accessed: Oct. 22, 2026.

[12] Groq, “GPT-OSS 120B Model Documentation.” [Online]. Available: https://console.groq.com/docs/model/openai/gpt-oss-120b. Accessed: Oct. 22, 2026.

[13] Meta Prophet, “Quick Start.” [Online]. Available: https://facebook.github.io/prophet/docs/quick_start. Accessed: Oct. 22, 2026.

[14] scikit-learn Developers, “KMeans.” [Online]. Available: https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html. Accessed: Oct. 22, 2026.

[15] XGBoost Developers, “Python API Reference.” [Online]. Available: https://xgboost.readthedocs.io/en/latest/python/python_api.html. Accessed: Oct. 22, 2026.

---

# 12. Appendices

## Appendix A — Abbreviations

| Abbreviation | Meaning |
|---|---|
| AI | Artificial Intelligence |
| API | Application Programming Interface |
| BI | Business Intelligence |
| CSV | Comma-Separated Values |
| ETL | Extract, Transform, Load |
| FK | Foreign Key |
| KPI | Key Performance Indicator |
| LLM | Large Language Model |
| ML | Machine Learning |
| NL | Natural Language |
| OLAP | Online Analytical Processing |
| PK | Primary Key |
| RFM | Recency, Frequency, Monetary |
| SQL | Structured Query Language |
| UI | User Interface |
| XLS/XLSX | Microsoft Excel spreadsheet formats |

## Appendix B — Selected API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| /health | GET | API and database health response. |
| /ready | GET | Database readiness response. |
| /metrics | GET | Prometheus-compatible request metrics. |
| /api/upload | POST | Upload files and start the ETL workflow. |
| /api/schema/{session_id} | GET | Retrieve detected tables, columns, relationships, and saved quality summaries. |
| /api/status/{session_id} | GET | Retrieve upload/ETL status. |
| /api/analytics/{session_id} | GET | Retrieve session KPIs and chart metadata, with optional filters. |
| /api/analytics/{session_id}/chart/{chart_id} | GET | Retrieve chart data. |
| /api/analytics/{session_id}/comparison | GET | Compare selected-period KPIs with the previous period. |
| /api/analytics/{session_id}/what-if | POST | Calculate KPI projections from percentage adjustments. |
| /api/chat | POST | Submit a natural-language question for a session. |
| /api/chat/{session_id}/history | GET | Retrieve saved chat history. |
| /api/reports/{session_id}.pdf | GET | Generate a PDF report using session data and optional filters. |
| /api/analytics/{session_id}/share | POST | Create a time-limited read-only share token. |
| /api/shared/{token} | GET | Retrieve a public read-only dashboard for a valid share token. |
| /api/ml/train?model_type=... | POST | Train a supported model from prepared CSV input. |

The API routes are protected according to application environment and session ownership rules. Some optional backend endpoints do not have a dedicated user-facing interface in the reviewed frontend.

## Appendix C — Screenshot and Diagram Prompts

Use actual screenshots from the running project or the Review 2 deck for application evidence. Do not generate fake screenshots of the interface. When a screenshot contains personal information, a live bearer token, an API key, or a real dataset value that should not be disclosed, crop or redact it before inserting it.

1. **Architecture diagram:** Use the exact prompt in Section 5.1.
2. **Use-case diagram:** Use the exact prompt in Section 3.5.
3. **ETL/data-flow diagram:** Use the exact prompt in Section 5.2.
4. **ER diagram:** Use the exact prompt in Section 5.4.
5. **Sequence diagram:** Use the exact prompt in Section 5.10.
6. **Application evidence:** Use the screenshot prompts in Section 8.4.

## Appendix D — Supporting Test Modules

The repository includes test modules for AI SQL safety, authentication hardening, analytics, KPI calculation and comparison, filters, ETL, schema detection, storage, health, metrics, notifications, rate limiting, production configuration, ML routes, workspace functions, and backup helpers. Refer to the dated Weekly Report 12 entry for the recorded aggregate test result.
