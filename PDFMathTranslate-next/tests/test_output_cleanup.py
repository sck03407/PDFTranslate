import os
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path

import pytest

from pdf2zh_next.output_cleanup import cleanup_session_output_dirs
from pdf2zh_next.output_cleanup import get_gui_output_root_dir
from pdf2zh_next.output_cleanup import is_session_output_dir


def _make_session_dir(base_dir: Path, *, days_old: int = 0) -> Path:
    session_dir = base_dir / str(uuid.uuid4())
    session_dir.mkdir(parents=True)
    timestamp = (
        datetime.now(timezone.utc) - timedelta(days=days_old)
    ).timestamp()
    os.utime(session_dir, (timestamp, timestamp))
    return session_dir


def test_is_session_output_dir_accepts_uuid_directory(tmp_path: Path):
    session_dir = _make_session_dir(tmp_path)

    assert is_session_output_dir(session_dir) is True


def test_is_session_output_dir_rejects_non_uuid_directory(tmp_path: Path):
    regular_dir = tmp_path / "not-a-session"
    regular_dir.mkdir()

    assert is_session_output_dir(regular_dir) is False


def test_cleanup_session_output_dirs_removes_only_expired_session_dirs(
    tmp_path: Path,
):
    expired_dir = _make_session_dir(tmp_path, days_old=10)
    fresh_dir = _make_session_dir(tmp_path, days_old=1)
    note_file = tmp_path / "README.txt"
    note_file.write_text("keep me", encoding="utf-8")

    result = cleanup_session_output_dirs(base_dir=tmp_path, older_than_days=7)

    assert expired_dir in result.deleted_dirs
    assert fresh_dir in result.kept_dirs
    assert note_file in result.skipped_non_session_entries
    assert expired_dir.exists() is False
    assert fresh_dir.exists() is True
    assert note_file.exists() is True


def test_cleanup_session_output_dirs_can_keep_specific_session_ids(tmp_path: Path):
    kept_dir = _make_session_dir(tmp_path, days_old=30)
    removed_dir = _make_session_dir(tmp_path, days_old=30)

    result = cleanup_session_output_dirs(
        base_dir=tmp_path,
        remove_all=True,
        keep_session_ids=[kept_dir.name],
    )

    assert kept_dir in result.kept_dirs
    assert removed_dir in result.deleted_dirs
    assert kept_dir.exists() is True
    assert removed_dir.exists() is False


def test_cleanup_session_output_dirs_rejects_invalid_retention_days(tmp_path: Path):
    with pytest.raises(
        ValueError, match="older_than_days must be greater than or equal to 1"
    ):
        cleanup_session_output_dirs(base_dir=tmp_path, older_than_days=0)


def test_gui_output_root_prefers_runtime_directory(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("PDF2ZH_OUTPUT_DIR", raising=False)
    monkeypatch.setenv("PDF2ZH_RUNTIME_DIR", str(tmp_path))

    assert get_gui_output_root_dir() == tmp_path / "pdf2zh_files"


def test_gui_output_root_can_be_overridden(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "outputs"
    monkeypatch.setenv("PDF2ZH_OUTPUT_DIR", str(output_dir))

    assert get_gui_output_root_dir() == output_dir
