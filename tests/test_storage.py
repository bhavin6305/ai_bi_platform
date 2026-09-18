from pathlib import Path

from etl.storage import LocalUploadStorage, S3UploadStorage


class FakeS3:
    def __init__(self):
        self.uploads = []
        self.downloads = []
        self.deletes = []

    def upload_file(self, filename, bucket, key):
        self.uploads.append((filename, bucket, key))

    def download_file(self, bucket, key, filename):
        self.downloads.append((bucket, key, filename))
        Path(filename).write_text("data", encoding="utf-8")

    def delete_object(self, **kwargs):
        self.deletes.append(kwargs)


def test_s3_storage_round_trips_locations(tmp_path):
    client = FakeS3()
    storage = S3UploadStorage("analytics", "uploads", client=client)
    source = tmp_path / "source.csv"
    source.write_text("id\n1\n", encoding="utf-8")

    location = storage.put(source, "session/file.csv")
    destination = storage.get(location, tmp_path / "download.csv")
    storage.delete(location)

    assert location == "s3://analytics/uploads/session/file.csv"
    assert destination.read_text(encoding="utf-8") == "data"
    assert client.deletes == [{"Bucket": "analytics", "Key": "uploads/session/file.csv"}]


def test_local_storage_keeps_staged_file_in_place(tmp_path):
    source = tmp_path / "upload.csv"
    source.write_text("data", encoding="utf-8")

    location = LocalUploadStorage(tmp_path).put(source, source.name)

    assert Path(location).read_text(encoding="utf-8") == "data"