import json
import sqlite3

import pytest

from journal_storage import JournalDatabase, QSO_FIELDS


def make_qso(call, **overrides):
    qso = {field: "" for field in QSO_FIELDS}
    qso.update({"call": call, **overrides})
    return qso


def test_replace_all_failure_rolls_back_and_preserves_previous_journal(tmp_path):
    db = JournalDatabase(tmp_path / "blind_log.db")
    original = [make_qso("OLD", comment="keep this record")]
    db.replace_all(original)

    with sqlite3.connect(db.path) as connection:
        connection.execute("""
            CREATE TRIGGER fail_selected_qso BEFORE INSERT ON qsos
            WHEN NEW.call = 'FAIL'
            BEGIN
                SELECT RAISE(ABORT, 'simulated disk/write failure');
            END
        """)

    with pytest.raises(sqlite3.IntegrityError, match="simulated disk/write failure"):
        db.replace_all([make_qso("NEW"), make_qso("FAIL")])

    assert db.get_all() == original


def test_delete_failure_rolls_back_record_and_positions(tmp_path):
    db = JournalDatabase(tmp_path / "blind_log.db")
    original = [make_qso("FIRST"), make_qso("SECOND"), make_qso("THIRD")]
    db.replace_all(original)

    with sqlite3.connect(db.path) as connection:
        connection.execute("""
            CREATE TRIGGER fail_reposition BEFORE UPDATE OF position ON qsos
            WHEN NEW.position >= 1000000000
            BEGIN
                SELECT RAISE(ABORT, 'simulated reposition failure');
            END
        """)

    with pytest.raises(sqlite3.IntegrityError, match="simulated reposition failure"):
        db.delete_at(0)

    assert db.get_all() == original


def test_draft_replace_failure_keeps_previous_draft_and_cleans_temp_file(tmp_path, monkeypatch):
    import journal_storage

    db = JournalDatabase(tmp_path / "blind_log.db")
    draft_path = tmp_path / "qso_draft.json"
    previous = {"version": 1, "fields": {"call": "R1BQE", "comment": "previous draft"}}
    db.save_draft(draft_path, previous)

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(journal_storage.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        db.save_draft(draft_path, {"version": 1, "fields": {"call": "NEW"}})

    assert json.loads(draft_path.read_text(encoding="utf-8")) == previous
    assert list(tmp_path.glob("qso_draft.json.*.tmp")) == []


def test_backup_is_readable_and_contains_complete_journal(tmp_path):
    db = JournalDatabase(tmp_path / "blind_log.db")
    original = [make_qso("R1BQE", comment="backup check"), make_qso("DL1ABC")]
    db.replace_all(original)

    backup_path = db.create_backup()

    assert backup_path is not None
    backup = JournalDatabase(backup_path)
    assert backup.get_all() == original


def test_empty_journal_does_not_create_unnecessary_backup(tmp_path):
    db = JournalDatabase(tmp_path / "blind_log.db")
    assert db.create_backup() is None
