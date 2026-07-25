"""
Quick test for the schema_detection module.
Run this from the project root with:
    python tests/test_schema_detection.py
"""

import logging
import json

# Show all debug logs so you can see what the detector is thinking
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

from schema_detection import profile_upload

# ── Simulate file uploads using real Olist files ───────────────────────────

class FakeUpload:
    """Mimics a FastAPI UploadFile object for local testing."""
    def __init__(self, filepath):
        self.filename = filepath.split("\\")[-1].split("/")[-1]
        self.file     = open(filepath, "rb")

files = [
    FakeUpload("data/raw/olist_orders_dataset.csv"),
    FakeUpload("data/raw/olist_customers_dataset.csv"),
    FakeUpload("data/raw/olist_order_items_dataset.csv"),
    FakeUpload("data/raw/olist_products_dataset.csv"),
]

# ── Run the full schema detection pipeline ─────────────────────────────────

print("\n" + "="*60)
print("Running schema detection on 3 Olist files...")
print("="*60 + "\n")

result = profile_upload(files, session_id="test-session-001")

# ── Print results ──────────────────────────────────────────────────────────

response = result.to_api_response()
print(json.dumps(response, indent=2))

# ── Quick assertions — these should all pass ───────────────────────────────

print("\n" + "="*60)
print("Running assertions...")
print("="*60)

for file_profile in result.files:
    col_types = {c["column_name"]: c["detected_type"] for c in file_profile.columns}
    print(f"\nTable: {file_profile.table_name}")
    for col, typ in col_types.items():
        print(f"  {col:40s} → {typ}")

print(f"\nRelationships found: {len(result.relationships)}")
for rel in result.relationships:
    print(f"  {rel['from_table']}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']} | {rel['confidence']} | {rel['match_percent']}%")

print(f"\nOverall quality score: {result.overall_quality}/100")
print("\n✓ Done. Check the output above for correctness.")