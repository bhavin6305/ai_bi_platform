import logging
import os
import tempfile
from pathlib import Path

from etl.job_queue import get_etl_queue
from etl.pipeline import run_pipeline
from etl.storage import get_upload_storage

logger = logging.getLogger(__name__)


def process_next_job(queue=None) -> bool:
    queue = queue or get_etl_queue()
    job = queue.dequeue(timeout=1)
    if job is None:
        return False

    try:
        storage = get_upload_storage()
        local_paths = []
        temporary_dir = Path(tempfile.mkdtemp(prefix="aibi-etl-"))
        for index, location in enumerate(job.file_paths):
            if location.startswith("s3://"):
                local_paths.append(str(storage.get(location, temporary_dir / f"upload-{index}")))
            else:
                local_paths.append(location)
        run_pipeline(files=local_paths, session_id=job.session_id)
    except Exception:
        logger.exception("ETL job failed for session %s", job.session_id)
    finally:
        for file_path in job.file_paths:
            try:
                storage.delete(file_path)
            except OSError:
                logger.warning("Unable to remove staged upload %s", file_path)
    return True


def run_worker() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    queue = get_etl_queue()
    logger.info("ETL worker started")
    while True:
        process_next_job(queue)


if __name__ == "__main__":
    run_worker()