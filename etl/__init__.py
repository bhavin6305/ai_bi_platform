"""
etl
---
ETL pipeline module for the AI-Powered BI Platform.

Public API:

    from etl import run_pipeline, run_pipeline_from_paths, PipelineResult

The FastAPI upload route uses run_pipeline().
CLI testing uses run_pipeline_from_paths().
"""

from etl.pipeline import run_pipeline, run_pipeline_from_paths, PipelineResult, get_engine
from etl.cleaner  import clean_table, clean_all_tables
from etl.extractor import extract_from_profile, extract_from_files

__all__ = [
    "run_pipeline",
    "run_pipeline_from_paths",
    "PipelineResult",
    "get_engine",
    "clean_table",
    "clean_all_tables",
    "extract_from_profile",
    "extract_from_files",
]