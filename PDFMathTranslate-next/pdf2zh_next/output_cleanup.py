from __future__ import annotations

import logging
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

GUI_OUTPUT_DIR_ENV = "PDF2ZH_OUTPUT_DIR"
RUNTIME_DIR_ENV = "PDF2ZH_RUNTIME_DIR"


@dataclass(slots=True)
class CleanupResult:
    base_dir: Path
    deleted_dirs: list[Path]
    kept_dirs: list[Path]
    skipped_non_session_entries: list[Path]
    errors: list[str]


def get_gui_output_root_dir() -> Path:
    output_dir = os.getenv(GUI_OUTPUT_DIR_ENV)
    if output_dir:
        return Path(output_dir).expanduser()

    runtime_dir = os.getenv(RUNTIME_DIR_ENV)
    if runtime_dir:
        return Path(runtime_dir).expanduser() / "pdf2zh_files"

    return Path.cwd() / "pdf2zh_files"


def is_session_output_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        uuid.UUID(path.name)
    except ValueError:
        return False
    return True


def iter_session_output_dirs(base_dir: Path | None = None) -> list[Path]:
    resolved_base_dir = Path(base_dir or get_gui_output_root_dir())
    if not resolved_base_dir.exists():
        return []
    return sorted(
        [child for child in resolved_base_dir.iterdir() if is_session_output_dir(child)],
        key=lambda path: path.name,
    )


def cleanup_session_output_dirs(
    *,
    base_dir: Path | None = None,
    older_than_days: int | None = None,
    keep_session_ids: Iterable[str] | None = None,
    remove_all: bool = False,
    now: datetime | None = None,
) -> CleanupResult:
    resolved_base_dir = Path(base_dir or get_gui_output_root_dir())
    keep_ids = {session_id for session_id in (keep_session_ids or []) if session_id}

    deleted_dirs: list[Path] = []
    kept_dirs: list[Path] = []
    skipped_non_session_entries: list[Path] = []
    errors: list[str] = []

    if not resolved_base_dir.exists():
        return CleanupResult(
            base_dir=resolved_base_dir,
            deleted_dirs=deleted_dirs,
            kept_dirs=kept_dirs,
            skipped_non_session_entries=skipped_non_session_entries,
            errors=errors,
        )

    if not remove_all and older_than_days is None:
        raise ValueError("older_than_days must be provided when remove_all is False")
    if older_than_days is not None and older_than_days < 1:
        raise ValueError("older_than_days must be greater than or equal to 1")

    current_time = now or datetime.now(timezone.utc)
    cutoff = (
        current_time - timedelta(days=older_than_days)
        if older_than_days is not None
        else None
    )

    for child in sorted(resolved_base_dir.iterdir(), key=lambda path: path.name):
        if not is_session_output_dir(child):
            skipped_non_session_entries.append(child)
            continue

        if child.name in keep_ids:
            kept_dirs.append(child)
            continue

        should_delete = remove_all
        if not should_delete and cutoff is not None:
            modified_time = datetime.fromtimestamp(
                child.stat().st_mtime,
                tz=timezone.utc,
            )
            should_delete = modified_time < cutoff

        if not should_delete:
            kept_dirs.append(child)
            continue

        try:
            shutil.rmtree(child)
            deleted_dirs.append(child)
        except OSError as exc:
            message = f"Failed to remove {child}: {exc}"
            logger.warning(message)
            errors.append(message)
            kept_dirs.append(child)

    return CleanupResult(
        base_dir=resolved_base_dir,
        deleted_dirs=deleted_dirs,
        kept_dirs=kept_dirs,
        skipped_non_session_entries=skipped_non_session_entries,
        errors=errors,
    )
