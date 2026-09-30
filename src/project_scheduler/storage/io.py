"""Loading and saving. ``load`` never raises; ``save`` writes atomically."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from ..domain import Project
from ..domain.validation import validate_project
from .format import FORMAT_VERSION, FormatError, document_from_project, migrate, project_from_document


class LoadStatus(Enum):
    OK = "ok"
    MISSING = "missing"
    CORRUPT = "corrupt"
    TOO_NEW = "too_new"
    MIGRATED = "migrated"


class MessageCode(Enum):
    NONE = "none"
    FILE_MISSING = "file_missing"
    FILE_CORRUPT = "file_corrupt"
    FILE_CORRUPT_NOT_BACKED_UP = "file_corrupt_not_backed_up"
    FILE_TOO_NEW = "file_too_new"
    FILE_MIGRATED = "file_migrated"


@dataclass(frozen=True)
class LoadResult:
    project: Project
    status: LoadStatus
    message_code: MessageCode
    backup_path: Path | None = None


def _backup_corrupt(path: Path, now: datetime) -> Path | None:
    stamp = now.strftime("%Y%m%d-%H%M%S")
    target = path.with_name(f"{path.name}.corrupt-{stamp}")
    n = 1
    while target.exists():
        target = path.with_name(f"{path.name}.corrupt-{stamp}-{n}")
        n += 1
    try:
        os.replace(path, target)
    except OSError:
        return None
    return target


def load(path: Path, *, default_start: date | None = None, now: datetime | None = None) -> LoadResult:
    path = Path(path)
    empty = Project.new(default_start or date.today())

    def corrupt() -> LoadResult:
        backup = _backup_corrupt(path, now or datetime.now())
        code = MessageCode.FILE_CORRUPT if backup else MessageCode.FILE_CORRUPT_NOT_BACKED_UP
        return LoadResult(empty, LoadStatus.CORRUPT, code, backup)

    if not path.exists():
        return LoadResult(empty, LoadStatus.MISSING, MessageCode.FILE_MISSING)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return corrupt()

    if not isinstance(document, dict):
        return corrupt()
    version = document.get("format_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        return corrupt()
    if version > FORMAT_VERSION:
        return LoadResult(empty, LoadStatus.TOO_NEW, MessageCode.FILE_TOO_NEW)

    try:
        migrated = version < FORMAT_VERSION
        if migrated:
            document = migrate(document, version)
        project = project_from_document(document)
    except FormatError:
        return corrupt()
    if validate_project(project):
        return corrupt()
    if migrated:
        return LoadResult(project, LoadStatus.MIGRATED, MessageCode.FILE_MIGRATED)
    return LoadResult(project, LoadStatus.OK, MessageCode.NONE)


def save(project: Project, path: Path) -> None:
    """Write to ``<name>.tmp``, fsync, then atomically replace ``path``. Raises OSError on failure."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    text = json.dumps(document_from_project(project), ensure_ascii=False, indent=2)
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
