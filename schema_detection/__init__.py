"""
schema_detection
----------------
Auto schema detection module for the AI-Powered BI Platform.

Public API — import only from here, not from submodules directly:

    from schema_detection import profile_upload, SessionProfile

The rest of the system (FastAPI routes, ETL pipeline) should only
ever import from this __init__.py. This way, if internal file names
change, only this file needs updating — not every import across the project.
"""

from schema_detection.profiler              import profile_upload, SessionProfile, FileProfile
from schema_detection.type_detector         import detect_column_type, detect_all_columns
from schema_detection.relationship_detector import detect_relationships
from schema_detection.quality_reporter      import generate_quality_report, QualityReport

__all__ = [
    # Main entry point — use this for normal usage
    "profile_upload",

    # Data classes — use these for type hints
    "SessionProfile",
    "FileProfile",
    "QualityReport",

    # Lower-level functions — use these only if you need fine-grained control
    "detect_column_type",
    "detect_all_columns",
    "detect_relationships",
    "generate_quality_report",
]