import json
import shutil
from datetime import date, datetime
from pathlib import Path

import pytest

from project_scheduler.domain import Project, Task, WorkCalendar
from project_scheduler.storage import FORMAT_VERSION, LoadStatus, MessageCode, format as fmt, io, load, save

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 1, 2, 3, 4, 5)
DEFAULT_START = date(2026, 3, 2)


def sample_project() -> Project:
    cal = WorkCalendar(date(2026, 1, 2), frozenset({0, 1, 2, 3}), frozenset({date(2026, 1, 6)}))
    return Project(cal, [Task(1, "Désign 設計", 3), Task(2, "Build", 0, [1])], 5)


def write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def assert_corrupt(path: Path, original: str) -> None:
    result = load(path, default_start=DEFAULT_START, now=NOW)
    assert result.status is LoadStatus.CORRUPT
    assert result.message_code is MessageCode.FILE_CORRUPT
    assert result.project == Project.new(DEFAULT_START)
    assert result.backup_path == path.with_name(f"{path.name}.corrupt-20260102-030405")
    assert result.backup_path.read_text(encoding="utf-8") == original
    assert not path.exists()


def test_round_trip(tmp_path):
    path = tmp_path / "p.schedule.json"
    project = sample_project()
    save(project, path)
    result = load(path)
    assert result.status is LoadStatus.OK
    assert result.message_code is MessageCode.NONE
    assert result.project == project
    assert json.loads(path.read_text(encoding="utf-8"))["format_version"] == FORMAT_VERSION


def test_missing_file(tmp_path):
    path = tmp_path / "nope.schedule.json"
    result = load(path, default_start=DEFAULT_START)
    assert result.status is LoadStatus.MISSING
    assert result.message_code is MessageCode.FILE_MISSING
    assert result.project.tasks == []
    assert not path.exists()


def test_invalid_json(tmp_path):
    path = write(tmp_path / "p.schedule.json", "{not json")
    assert_corrupt(path, "{not json")


def test_non_utf8_bytes(tmp_path):
    path = tmp_path / "p.schedule.json"
    path.write_bytes(b"\xff\xfe\x00garbage")
    result = load(path, now=NOW)
    assert result.status is LoadStatus.CORRUPT
    assert result.backup_path.exists()


@pytest.mark.parametrize("document", [
    [1, 2, 3],
    {"project": {}},
    {"format_version": "1", "project": {}},
    {"format_version": True, "project": {}},
    {"format_version": 0, "project": {}},
    {"format_version": 1},
    {"format_version": 1, "project": {"start_date": "2026-13-01", "calendar": {"working_weekdays": [0], "holidays": []}, "next_id": 1, "tasks": []}},
    {"format_version": 1, "project": {"start_date": "2026-01-01", "calendar": {"working_weekdays": [], "holidays": []}, "next_id": 1, "tasks": []}},
    {"format_version": 1, "project": {"start_date": "2026-01-01", "calendar": {"working_weekdays": [0], "holidays": []}, "next_id": 2,
                                      "tasks": [{"id": 1, "name": "A", "duration": "3", "predecessors": []}]}},
    {"format_version": 1, "project": {"start_date": "2026-01-01", "calendar": {"working_weekdays": [0], "holidays": []}, "next_id": 2,
                                      "tasks": [{"id": 1, "name": "A", "duration": 3}]}},
])
def test_valid_json_with_wrong_shape(tmp_path, document):
    text = json.dumps(document)
    assert_corrupt(write(tmp_path / "p.schedule.json", text), text)


def test_valid_shape_that_breaks_the_rules(tmp_path):
    document = {"format_version": 1, "project": {
        "start_date": "2026-01-01", "calendar": {"working_weekdays": [0], "holidays": []}, "next_id": 3,
        "tasks": [{"id": 1, "name": "A", "duration": 1, "predecessors": [2]},
                  {"id": 2, "name": "B", "duration": 1, "predecessors": [1]}]}}
    text = json.dumps(document)
    assert_corrupt(write(tmp_path / "p.schedule.json", text), text)


def test_too_new(tmp_path):
    text = json.dumps({"format_version": FORMAT_VERSION + 1, "project": {"anything": True}})
    path = write(tmp_path / "p.schedule.json", text)
    result = load(path, default_start=DEFAULT_START)
    assert result.status is LoadStatus.TOO_NEW
    assert result.message_code is MessageCode.FILE_TOO_NEW
    assert result.project.tasks == []
    assert path.read_text(encoding="utf-8") == text  # left alone


def test_second_corrupt_backup_in_same_second_gets_unique_name(tmp_path):
    path = tmp_path / "p.schedule.json"
    first = load(write(path, "x"), now=NOW).backup_path
    second = load(write(path, "y"), now=NOW).backup_path
    assert first != second
    assert first.read_text() == "x" and second.read_text() == "y"


def test_every_old_version_has_a_migration():
    for version in range(1, FORMAT_VERSION):
        assert version in fmt.MIGRATIONS, f"missing migrate_v{version}_to_v{version + 1}"


@pytest.mark.parametrize("fixture", sorted(FIXTURES.glob("v*_*.schedule.json")), ids=lambda p: p.name)
def test_every_fixture_loads(tmp_path, fixture):
    path = tmp_path / fixture.name
    shutil.copy(fixture, path)
    result = load(path)
    expected = LoadStatus.OK if fixture.name.startswith(f"v{FORMAT_VERSION}_") else LoadStatus.MIGRATED
    assert result.status is expected
    assert [t.name for t in result.project.tasks] == ["Design", "Build", "Launch"]


def test_migration_mechanism(tmp_path, monkeypatch):
    """Simulate the next format version so the generic migrate path is exercised."""
    current = FORMAT_VERSION

    def migrate_to_next(document):
        document["project"]["tasks"][0]["name"] = "Design (migrated)"
        return document

    path = tmp_path / "old.schedule.json"
    save(sample_project(), path)  # written at the current version
    monkeypatch.setattr(fmt, "FORMAT_VERSION", current + 1)
    monkeypatch.setattr(io, "FORMAT_VERSION", current + 1)
    monkeypatch.setitem(fmt.MIGRATIONS, current, migrate_to_next)
    result = load(path)
    assert result.status is LoadStatus.MIGRATED
    assert result.message_code is MessageCode.FILE_MIGRATED
    assert result.project.tasks[0].name == "Design (migrated)"


def test_missing_migration_is_corrupt(tmp_path, monkeypatch):
    path = tmp_path / "old.schedule.json"
    save(sample_project(), path)
    monkeypatch.setattr(fmt, "FORMAT_VERSION", FORMAT_VERSION + 1)
    monkeypatch.setattr(io, "FORMAT_VERSION", FORMAT_VERSION + 1)
    assert load(path, now=NOW).status is LoadStatus.CORRUPT


def test_v1_file_migrates_to_v2_with_empty_notes(tmp_path):
    path = tmp_path / "v1.schedule.json"
    shutil.copy(FIXTURES / "v1_project.schedule.json", path)
    result = load(path)
    assert result.status is LoadStatus.MIGRATED
    assert [t.notes for t in result.project.tasks] == ["", "", ""]
    assert [t.predecessors for t in result.project.tasks] == [[], [1], [2]]  # nothing else changed


def test_notes_round_trip(tmp_path):
    project = sample_project()
    project.tasks[0].notes = "Waiting on vendor\nsecond line — ümlaut 日本語"
    path = tmp_path / "p.schedule.json"
    save(project, path)
    assert load(path).project.tasks[0].notes == project.tasks[0].notes


def test_notes_with_wrong_type_is_corrupt(tmp_path):
    document = {"format_version": FORMAT_VERSION, "project": {
        "start_date": "2026-01-01", "calendar": {"working_weekdays": [0], "holidays": []}, "next_id": 2,
        "tasks": [{"id": 1, "name": "A", "duration": 1, "predecessors": [], "notes": 42}]}}
    text = json.dumps(document)
    assert_corrupt(write(tmp_path / "p.schedule.json", text), text)


def test_save_is_atomic_and_leaves_no_temp_file(tmp_path):
    path = write(tmp_path / "p.schedule.json", "old")
    save(sample_project(), path)
    assert not (tmp_path / "p.schedule.json.tmp").exists()
    assert load(path).status is LoadStatus.OK


def test_failed_save_raises_and_cleans_up(tmp_path, monkeypatch):
    path = tmp_path / "p.schedule.json"
    write(path, "keep me")

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(io.os, "replace", boom)
    with pytest.raises(OSError):
        save(sample_project(), path)
    assert path.read_text() == "keep me"
    assert not (tmp_path / "p.schedule.json.tmp").exists()
