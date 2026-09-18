import pytest

from ops.database_backup import create_backup, restore_backup, verify_backup


def test_create_backup_invokes_pg_dump(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setenv("DB_URL", "postgresql://db.example/analytics")

    def runner(command, **kwargs):
        calls.append(command)

    destination = create_backup(tmp_path / "backup.dump", runner=runner)

    assert destination.exists() is False
    assert calls[0][0:3] == ["pg_dump", "--format=custom", "--no-owner"]
    assert calls[0][-1] == "postgresql://db.example/analytics"


def test_verify_backup_invokes_pg_restore(tmp_path):
    calls = []

    def runner(command, **kwargs):
        calls.append(command)

    assert verify_backup(tmp_path / "backup.dump", runner=runner) is True
    assert calls[0][:2] == ["pg_restore", "--list"]


def test_restore_requires_explicit_confirmation():
    with pytest.raises(ValueError, match="allow_destructive"):
        restore_backup("backup.dump", runner=lambda *args, **kwargs: None)