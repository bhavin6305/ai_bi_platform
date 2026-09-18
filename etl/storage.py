import os
from pathlib import Path


class LocalUploadStorage:
    def __init__(self, root: str | Path = "data/staging"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, source: Path, key: str) -> str:
        destination = self.root / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != destination.resolve():
            source.replace(destination)
        return str(destination)

    def get(self, location: str, destination: Path) -> Path:
        source = Path(location)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        return destination

    def delete(self, location: str) -> None:
        Path(location).unlink(missing_ok=True)


class S3UploadStorage:
    def __init__(self, bucket: str, prefix: str = "uploads", client=None):
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        if client is None:
            import boto3

            client = boto3.client("s3", endpoint_url=os.getenv("S3_ENDPOINT_URL") or None)
        self.client = client

    def put(self, source: Path, key: str) -> str:
        object_key = f"{self.prefix}/{key}" if self.prefix else key
        self.client.upload_file(str(source), self.bucket, object_key)
        return f"s3://{self.bucket}/{object_key}"

    def get(self, location: str, destination: Path) -> Path:
        bucket, _, key = location[5:].partition("/")
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(bucket, key, str(destination))
        return destination

    def delete(self, location: str) -> None:
        bucket, _, key = location[5:].partition("/")
        self.client.delete_object(Bucket=bucket, Key=key)


def get_upload_storage():
    backend = os.getenv("UPLOAD_STORAGE", "local").strip().lower()
    if backend != "s3":
        return LocalUploadStorage(os.getenv("UPLOAD_STAGING_DIR", "data/staging"))

    bucket = os.getenv("S3_BUCKET", "").strip()
    if not bucket:
        raise ValueError("S3_BUCKET is required when UPLOAD_STORAGE=s3")
    return S3UploadStorage(bucket, os.getenv("S3_PREFIX", "uploads"))