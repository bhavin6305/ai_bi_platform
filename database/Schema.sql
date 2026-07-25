-- ============================================================
-- AI-Powered BI Platform — Database Schema
-- Layer 1: Platform Metadata Tables
-- Run this ONCE to initialize the platform database
-- ============================================================

-- Drop tables if re-running (for development resets)
DROP TABLE IF EXISTS ai_insights          CASCADE;
DROP TABLE IF EXISTS chart_configs        CASCADE;
DROP TABLE IF EXISTS kpi_results          CASCADE;
DROP TABLE IF EXISTS quality_reports      CASCADE;
DROP TABLE IF EXISTS detected_relationships CASCADE;
DROP TABLE IF EXISTS schema_profiles      CASCADE;
DROP TABLE IF EXISTS uploaded_files       CASCADE;
DROP TABLE IF EXISTS upload_sessions      CASCADE;

-- 1. Upload Sessions
CREATE TABLE upload_sessions (
    session_id        VARCHAR(36)  PRIMARY KEY,
    created_at        TIMESTAMP    DEFAULT NOW(),
    status            VARCHAR(20)  DEFAULT 'pending',
    total_files       INTEGER      DEFAULT 0,
    total_rows        BIGINT       DEFAULT 0,
    error_message     TEXT,
    completed_at      TIMESTAMP
);

-- 2. Uploaded Files
CREATE TABLE uploaded_files (
    file_id           SERIAL       PRIMARY KEY,
    session_id        VARCHAR(36)  REFERENCES upload_sessions(session_id),
    original_filename VARCHAR(255) NOT NULL,
    table_name        VARCHAR(255) NOT NULL,
    file_size_bytes   BIGINT,
    row_count         INTEGER,
    column_count      INTEGER,
    encoding          VARCHAR(50),
    uploaded_at       TIMESTAMP    DEFAULT NOW()
);

-- 3. Schema Profiles
CREATE TABLE schema_profiles (
    profile_id        SERIAL       PRIMARY KEY,
    session_id        VARCHAR(36)  REFERENCES upload_sessions(session_id),
    table_name        VARCHAR(255) NOT NULL,
    column_name       VARCHAR(255) NOT NULL,
    detected_type     VARCHAR(50)  NOT NULL,
    null_count        INTEGER      DEFAULT 0,
    null_percent      FLOAT        DEFAULT 0.0,
    unique_count      INTEGER,
    sample_values     TEXT,
    column_order      INTEGER
);

-- 4. Detected Relationships
CREATE TABLE detected_relationships (
    relationship_id   SERIAL       PRIMARY KEY,
    session_id        VARCHAR(36)  REFERENCES upload_sessions(session_id),
    from_table        VARCHAR(255) NOT NULL,
    from_column       VARCHAR(255) NOT NULL,
    to_table          VARCHAR(255) NOT NULL,
    to_column         VARCHAR(255) NOT NULL,
    confidence        VARCHAR(10)  NOT NULL,
    match_percent     FLOAT,
    view_name         VARCHAR(255)
);

-- 5. Quality Reports
CREATE TABLE quality_reports (
    report_id         SERIAL       PRIMARY KEY,
    session_id        VARCHAR(36)  REFERENCES upload_sessions(session_id),
    table_name        VARCHAR(255) NOT NULL,
    quality_score     INTEGER      NOT NULL,
    total_rows        INTEGER,
    duplicate_rows    INTEGER      DEFAULT 0,
    columns_with_nulls INTEGER     DEFAULT 0,
    outlier_columns   INTEGER      DEFAULT 0,
    issues_found      TEXT,
    actions_taken     TEXT,
    generated_at      TIMESTAMP    DEFAULT NOW()
);

-- 6. KPI Results
CREATE TABLE kpi_results (
    kpi_id            SERIAL       PRIMARY KEY,
    session_id        VARCHAR(36)  REFERENCES upload_sessions(session_id),
    kpi_name          VARCHAR(100) NOT NULL,
    kpi_value         FLOAT,
    kpi_unit          VARCHAR(20),
    kpi_category      VARCHAR(50),
    display_format    VARCHAR(50),
    calculated_at     TIMESTAMP    DEFAULT NOW()
);

-- 7. Chart Configs
CREATE TABLE chart_configs (
    chart_id          SERIAL       PRIMARY KEY,
    session_id        VARCHAR(36)  REFERENCES upload_sessions(session_id),
    chart_type        VARCHAR(30)  NOT NULL,
    chart_title       VARCHAR(255),
    source_table      VARCHAR(255),
    x_column          VARCHAR(255),
    y_column          VARCHAR(255),
    group_by_column   VARCHAR(255),
    aggregation       VARCHAR(20),
    chart_order       INTEGER,
    rationale         TEXT,
    plotly_config     TEXT,
    created_at        TIMESTAMP    DEFAULT NOW()
);

-- 8. AI Insights
CREATE TABLE ai_insights (
    insight_id        SERIAL       PRIMARY KEY,
    session_id        VARCHAR(36)  REFERENCES upload_sessions(session_id),
    insight_type      VARCHAR(30)  NOT NULL,
    chart_id          INTEGER      REFERENCES chart_configs(chart_id),
    question_asked    TEXT,
    sql_used          TEXT,
    insight_text      TEXT         NOT NULL,
    generated_at      TIMESTAMP    DEFAULT NOW()
);

-- ============================================================
-- Verification query — run after creating to confirm all 8 tables exist
-- ============================================================
SELECT table_name
FROM   information_schema.tables
WHERE  table_schema = 'public'
ORDER  BY table_name;
