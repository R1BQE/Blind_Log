from datetime import datetime


def test_add_qso_full(qso_manager):
    qso_data = {
        'call': 'test1',
        'name': 'Ivan Ivanov',
        'city': 'Moscow',
        'qth': 'kn18yv',
        'band': '40m',
        'mode': 'SSB',
        'freq': '7,100',
        'rst_received': '59',
        'rst_sent': '59',
        'comment': 'test comment',
        'datetime': '2025-01-01 12:00',
    }

    result = qso_manager.add_qso(qso_data)

    assert result.success is True
    assert result.error is None
    assert result.data is not None
    assert len(qso_manager.qso_list) == 1

    qso = qso_manager.qso_list[0]
    assert qso['call'] == 'TEST1'
    assert qso['name'] == 'Ivan Ivanov'
    assert qso['city'] == 'Moscow'
    assert qso['qth'] == 'KN18YV'
    assert qso['band'] == '40m'
    assert qso['mode'] == 'SSB'
    assert qso['freq'] == '7.100'
    assert qso['rst_received'] == '59'
    assert qso['rst_sent'] == '59'
    assert qso['comment'] == 'test comment'
    assert qso['datetime'] == '2025-01-01 12:00'


def test_add_qso_minimal(qso_manager):
    result = qso_manager.add_qso({'call': 'minimal'})

    assert result.success is True
    assert result.error is None
    assert len(qso_manager.qso_list) == 1
    qso = qso_manager.qso_list[0]
    assert qso['call'] == 'MINIMAL'
    assert qso['datetime']

    # Проверка формата даты/времени с секундами или без
    try:
        datetime.strptime(qso['datetime'], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        datetime.strptime(qso['datetime'], '%Y-%m-%d %H:%M')


def test_add_qso_invalid_data(qso_manager):
    result = qso_manager.add_qso({'call': ''})

    assert result.success is False
    assert 'callsign' in result.error.lower()
    assert len(qso_manager.qso_list) == 0


def test_edit_qso_updates_existing_record(qso_manager):
    qso_manager.add_qso({'call': 'first', 'datetime': '2025-01-01 12:00'})

    result = qso_manager.edit_qso(0, {
        'call': 'edited',
        'name': 'New Name',
        'qth': 'em10hd',
        'freq': '14.200',
        'mode': 'CW',
        'rst_received': '59',
        'rst_sent': '59',
        'comment': 'updated comment',
        'datetime': '2025-02-02 14:30',
    })

    assert result.success is True
    assert result.error is None
    assert len(qso_manager.qso_list) == 1

    qso = qso_manager.qso_list[0]
    assert qso['call'] == 'EDITED'
    assert qso['name'] == 'New Name'
    assert qso['qth'] == 'EM10HD'
    assert qso['freq'] == '14.200'
    assert qso['mode'] == 'CW'
    assert qso['comment'] == 'updated comment'
    assert qso['datetime'] == '2025-02-02 14:30'


def test_delete_qso_removes_record(qso_manager):
    qso_manager.add_qso({'call': 'one', 'datetime': '2026-01-01 10:00'})
    qso_manager.add_qso({'call': 'two', 'datetime': '2026-01-01 10:01'})

    assert len(qso_manager.qso_list) == 2
    assert [q['call'] for q in qso_manager.qso_list] == ['TWO', 'ONE']
    result = qso_manager.delete_qso(0)

    assert result.success is True
    assert len(qso_manager.qso_list) == 1
    assert qso_manager.qso_list[0]['call'] == 'ONE'



def test_delete_qso_invalid_index_returns_false(qso_manager):
    qso_manager.add_qso({'call': 'one'})

    result = qso_manager.delete_qso(5)

    assert result.success is False
    assert 'index' in result.error.lower()
    assert len(qso_manager.qso_list) == 1



def test_qso_is_persisted_after_manager_restart(settings_manager, monkeypatch, tmp_path):
    import qso_manager

    monkeypatch.setattr(qso_manager, "get_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(qso_manager, "get_app_path", lambda: str(tmp_path))
    first = qso_manager.QSOManager(settings_manager)
    result = first.add_qso({
        "call": "R1BQE",
        "name": "Иван",
        "comment": "Проверка постоянного журнала",
        "datetime": "2026-10-29 02:00",
    })
    assert result.success is True

    second = qso_manager.QSOManager(settings_manager)
    assert second.get_qso_count() == 1
    assert second.get_qso(0)["call"] == "R1BQE"
    assert second.get_qso(0)["name"] == "Иван"
    assert second.get_qso(0)["comment"] == "Проверка постоянного журнала"


def test_draft_survives_restart_and_can_be_cleared(settings_manager, monkeypatch, tmp_path):
    import qso_manager

    monkeypatch.setattr(qso_manager, "get_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(qso_manager, "get_app_path", lambda: str(tmp_path))
    first = qso_manager.QSOManager(settings_manager)
    fields = {
        "call": "R1BQE",
        "name": "Иван",
        "comment": "Незавершённая связь",
        "freq": "145.500",
        "date": "2026-10-29",
        "time": "02:00:00",
    }
    assert first.save_draft(fields).success is True

    second = qso_manager.QSOManager(settings_manager)
    assert second.load_draft()["fields"] == fields
    assert second.get_qso_count() == 0
    assert second.clear_draft().success is True
    assert second.load_draft() is None



def test_edit_and_delete_are_persisted(settings_manager, monkeypatch, tmp_path):
    import qso_manager

    monkeypatch.setattr(qso_manager, "get_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(qso_manager, "get_app_path", lambda: str(tmp_path))
    manager = qso_manager.QSOManager(settings_manager)
    assert manager.add_qso({"call": "FIRST", "datetime": "2026-01-01 10:00"}).success
    assert manager.add_qso({"call": "SECOND", "datetime": "2026-01-01 10:01"}).success
    assert manager.edit_qso(1, {
        "call": "UPDATED", "datetime": "2026-01-01 10:01", "comment": "edited"
    }).success

    restarted = qso_manager.QSOManager(settings_manager)
    assert [q["call"] for q in restarted.get_qso_list()] == ["SECOND", "UPDATED"]
    assert restarted.delete_qso(0).success

    restarted_again = qso_manager.QSOManager(settings_manager)
    assert restarted_again.get_qso_count() == 1
    assert restarted_again.get_qso(0)["call"] == "UPDATED"



def test_replace_import_creates_backup_of_existing_journal(settings_manager, monkeypatch, tmp_path):
    import qso_manager

    monkeypatch.setattr(qso_manager, "get_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(qso_manager, "get_app_path", lambda: str(tmp_path))
    manager = qso_manager.QSOManager(settings_manager)
    assert manager.add_qso({"call": "OLD", "datetime": "2026-01-01 10:00"}).success
    result = manager.import_qso_list([
        {"call": "NEW", "datetime": "2026-01-02 10:00"}
    ], mode="replace")
    assert result.success is True
    assert [q["call"] for q in manager.get_qso_list()] == ["NEW"]
    backups = list(tmp_path.glob("blind_log.db.*.bak"))
    assert len(backups) == 1



def test_qsos_are_sorted_newest_first_and_invalid_dates_last(qso_manager):
    qso_manager.qso_list = [
        {"call": "OLD", "datetime": "2024-01-01 09:00"},
        {"call": "INVALID", "datetime": "not-a-date"},
        {"call": "TODAY", "datetime": "2026-10-29 12:00"},
        {"call": "YESTERDAY", "datetime": "2026-10-28"},
        {"call": "NO-DATE", "datetime": ""},
        {"call": "EARLIER-TODAY", "datetime": "2026-10-29 08:00"},
    ]

    assert [q["call"] for q in qso_manager.get_qso_list()] == [
        "TODAY", "EARLIER-TODAY", "YESTERDAY", "OLD", "INVALID", "NO-DATE"
    ]


def test_imported_qsos_are_sorted_by_qso_datetime(qso_manager):
    result = qso_manager.import_qso_list([
        {"call": "OLD", "datetime": "2020-01-01 12:00"},
        {"call": "NEW", "datetime": "2026-10-29 12:00"},
        {"call": "MIDDLE", "datetime": "2024-05-01 12:00"},
    ], mode="replace")

    assert result.success is True
    assert [q["call"] for q in qso_manager.get_qso_list()] == ["NEW", "MIDDLE", "OLD"]


def test_equal_timestamps_keep_newly_added_qso_first(qso_manager):
    qso_manager.add_qso({"call": "FIRST", "datetime": "2026-10-29 12:00"})
    qso_manager.add_qso({"call": "SECOND", "datetime": "2026-10-29 12:00"})

    assert [q["call"] for q in qso_manager.get_qso_list()] == ["SECOND", "FIRST"]



def test_data_directory_is_next_to_the_application(monkeypatch, tmp_path):
    import utils

    monkeypatch.setattr(utils, "get_app_path", lambda: str(tmp_path))
    assert utils.get_data_dir() == str(tmp_path)
