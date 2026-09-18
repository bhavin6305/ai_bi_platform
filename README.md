# AI BI Platform

AI-powered business intelligence platform for uploading structured data, automatically detecting schemas, generating KPI analytics, producing chart recommendations, enabling AI-driven questions, and exporting executive PDF reports.

This project combines a Python FastAPI backend, PostgreSQL storage, AI SQL generation, and a frontend dashboard experience to create a complete analytics workflow from raw data to insights.

## Overview

The platform is designed to help users:

- upload one or more CSV/Excel files
- detect schema and relationships automatically
- clean and transform data into analytical tables
- generate KPIs and chart configurations
- filter data by date and category dimensions
- ask natural-language questions using SQL generation
- view saved chat history
- download PDF analytics reports
- receive session-scoped notifications
- manage authentication for protected deployment environments

## Core features

### Data ingestion and ETL
- upload support for CSV, Excel, and ZIP inputs
- schema profiling from uploaded files
- relationship detection between tables
- quality analysis and anomaly reporting
- SQL view creation for data access and analytics

### Analytics engine
- KPI calculation and comparison logic
- chart recommendation and chart configuration generation
- dashboard filter support by date and category
- chart data generation for frontend rendering

### AI and natural-language analytics
- Groq-based SQL generation from business questions
- read-only SQL validation to protect against unsafe queries
- result explanation and follow-up question suggestions
- saved AI chat history per session

### Machine learning
- train churn, monthly forecast, and RFM segmentation models from prepared CSVs
- persist versioned-ready model artifacts under `ML_MODEL_DIR` (default: `ml/models`)
- expose training through the protected `POST /api/ml/train?model_type=...` endpoint

### Reporting and notifications
- PDF report generation for session analytics
- notification persistence for pipeline and anomaly events
- read/unread notification tracking

### Authentication and production safety
- signup and signin endpoints
- bearer-token validation
- environment-aware production auth enforcement
- CORS and environment configuration controls
- retry logic for transient external failures

## Tech stack

### Backend
- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pandas / NumPy
- Pydantic
- python-dotenv

### AI and ML
- Groq API
- scikit-learn
- XGBoost
- Prophet
- joblib

### Frontend
- React + TypeScript
- Vite
- Tailwind-friendly component system

### Reporting and data processing
- ReportLab
- OpenPyXL
- Plotly
- Python multipart upload support

## Project structure

- [api](api) — FastAPI app, routes, database config, auth
- [analytics](analytics) — KPI logic, filters, chart generation, comparisons
- [ai](ai) — SQL generation, AI responses, insight generation
- [etl](etl) — extraction, cleaning, loading, and pipeline orchestration
- [data](data) — raw dataset sources
- [database](database) — SQL schema and analytical view definitions
- [ml](ml) — ML models and selectors
- [reports](reports) — report generation
- [schema_detection](schema_detection) — schema profiling and relationship analysis
- [tests](tests) — automated validation suite
- [Frontend](Frontend) — frontend dashboard and UI

## Prerequisites

- Python 3.11+
- PostgreSQL instance running locally or in a hosted environment
- Git
- Optional: Groq API key for AI SQL generation

## Quick start

### 1. Create and activate environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirement.txt
```

### 3. Configure environment variables

Copy [.env.example](.env.example) to `.env` and update values as needed.

Example variables:

- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `APP_ENV`
- `REQUIRE_AUTH`
- `CORS_ALLOW_ORIGINS`
- `RATE_LIMIT_REQUESTS` (default: 60 requests per window)
- `RATE_LIMIT_WINDOW_SECONDS` (default: 60 seconds)
- `REDIS_URL` (required for production-like deployments)
- `ETL_ASYNC` (set to `true` to use the Redis-backed ETL worker)
- `UPLOAD_STAGING_DIR` (default: `data/staging`)
- `UPLOAD_STORAGE` (`local` by default; use `s3` for distributed workers)
- `S3_BUCKET`, `S3_PREFIX`, `S3_ENDPOINT_URL` (required when using S3 storage)
- `GROQ_API_KEY`
- `JWT_SECRET_KEY`

### 4. Start the backend

```bash
uvicorn api.main:app --reload --port 8000
```

The API will be available at:

- http://localhost:8000
- http://localhost:8000/docs

Operational probes:

- `/health` reports API and database state for diagnostics.
- `/ready` returns HTTP 503 until the database dependency is available, making it suitable for load balancer readiness checks.

### 5. Start the frontend

From the [Frontend](Frontend) directory:

```bash
npm install
npm run dev
```

## API behavior

The backend exposes routes for:

- upload and ETL pipeline execution
- schema inspection and status checks
- analytics and KPI retrieval
- chart data access
- comparison analysis
- AI chat queries and saved history
- notifications
- report downloads
- auth signup/signin/settings

## Production guidance

This project is stable for controlled internal deployment and is structured to be extended safely. For production deployments:

- set `APP_ENV=production`
- set `REQUIRE_AUTH=true`
- restrict `CORS_ALLOW_ORIGINS` to trusted domains only
- configure `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` for expected traffic
- configure `REDIS_URL` so rate-limit counters are shared across API instances
- provide an explicit `DB_URL` or complete `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_NAME` values
- scrape `/metrics` through an internal monitoring network

For large uploads, set `ETL_ASYNC=true` and run a worker alongside the API:

```bash
python -m etl.worker
```

Uploaded files are staged temporarily, queued in Redis, processed by the worker,
and removed after processing. The upload endpoint returns HTTP 202 and the
existing `/api/status/{session_id}` endpoint reports progress.

For API and worker processes on different machines, use `UPLOAD_STORAGE=s3`
with an S3-compatible bucket and configure `S3_BUCKET`, `S3_PREFIX`, and AWS or
endpoint-specific credentials.

Create and verify database backups with:

```bash
python -m ops.database_backup backup backups/latest.dump
python -m ops.database_backup verify backups/latest.dump
python -m ops.database_backup restore backups/latest.dump --confirm-destructive-restore
```

The `/metrics` endpoint exposes Prometheus-compatible request counters and
latency buckets. Route its output to a monitoring system and alert on sustained
5xx responses, 429 responses, queue depth, and failed worker jobs.

Train an ML artifact by sending a prepared CSV to the API:

```bash
curl -X POST "http://localhost:8000/api/ml/train?model_type=segmentation" \
	-F "file=@customer_features.csv"
```

Use `model_type=churn` for customer rows containing the churn feature columns
and `churn_label`, `model_type=forecast` for `month` and `total_revenue`, or
`model_type=segmentation` for the RFM columns. In production, protect this
endpoint with authentication and point `ML_MODEL_DIR` at durable shared storage.
- store secrets in environment variables or a secret manager
- run PostgreSQL in a managed or dedicated environment
- monitor database and API health continuously

The application hardening baseline is implemented. Public SaaS deployment still
requires operating the external services and controls described above, including
secret management, PostgreSQL backup scheduling, Redis, object storage, and
monitoring alert rules.

API requests emit structured logs through the `api.requests` logger with method,
path, status code, duration, and a correlation ID. Responses include the same
correlation ID in the `X-Request-ID` header for incident tracing. Request bodies,
query values, and authorization headers are intentionally excluded.

## Testing

The project includes automated validation for analytics, ETL, filters, KPI logic, and production hardening checks.

Run the suite with:

```bash
python -m pytest -q
```

Current verified status:

- 31 tests passing in the workspace environment

## Status

The repository is in a working, validated, and production-hardened state for routine internal deployment use, with a clean path for future feature and deployment improvements.

## License

This project is intended for internal or educational business analytics use unless otherwise specified by the project owner.
