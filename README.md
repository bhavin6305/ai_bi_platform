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
- `GROQ_API_KEY`
- `JWT_SECRET_KEY`

### 4. Start the backend

```bash
uvicorn api.main:app --reload --port 8000
```

The API will be available at:

- http://localhost:8000
- http://localhost:8000/docs

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
- store secrets in environment variables or a secret manager
- run PostgreSQL in a managed or dedicated environment
- monitor database and API health continuously

This is a solid production-ready internal deployment baseline, but public SaaS production hardening still includes additional operational safeguards such as:

- secret management at scale
- rate limiting and abuse controls
- centralized logging and monitoring
- backup and restore validation
- queue-based async processing for very large data uploads

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
