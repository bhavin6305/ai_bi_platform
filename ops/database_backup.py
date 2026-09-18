"""PostgreSQL backup, archive verification, and explicitly confirmed restore helpers."""

import os
import subprocess
from pathlib import Path
from typing import Sequence

from api.database import build_database_url


def _database_url() -> str:
    return os.getenv("DB_URL") or build_database_url()


def create_backup(output_path: str | Path, runner=subprocess.run) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    runner(
        ["pg_dump", "--format=custom", "--no-owner", "--file", str(destination), _database_url()],
        check=True,
        capture_output=True,
        text=True,
    )
    return destination


def verify_backup(backup_path: str | Path, runner=subprocess.run) -> bool:
    runner(
        ["pg_restore", "--list", str(backup_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return True


def restore_backup(
    backup_path: str | Path,
    *,
    allow_destructive: bool = False,
    runner=subprocess.run,
) -> None:
    if not allow_destructive:
        raise ValueError("restore_backup requires allow_destructive=True")
    runner(
        [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--dbname",
            _database_url(),
            str(backup_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Manage AI BI Platform PostgreSQL backups")
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup = subparsers.add_parser("backup")
    backup.add_argument("path", type=Path)
    verify = subparsers.add_parser("verify")
    verify.add_argument("path", type=Path)
    restore = subparsers.add_parser("restore")
    restore.add_argument("path", type=Path)
    restore.add_argument("--confirm-destructive-restore", action="store_true")
    args = parser.parse_args()

    if args.command == "backup":
        create_backup(args.path)
    elif args.command == "verify":
        verify_backup(args.path)
    else:
        restore_backup(args.path, allow_destructive=args.confirm_destructive_restore)


if __name__ == "__main__":
    main()