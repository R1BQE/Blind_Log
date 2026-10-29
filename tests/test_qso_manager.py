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
    qso_manager.add_qso({'call': 'one'})
    qso_manager.add_qso({'call': 'two'})

    assert len(qso_manager.qso_list) == 2
    result = qso_manager.delete_qso(0)

    assert result.success is True
    assert len(qso_manager.qso_list) == 1
    assert qso_manager.qso_list[0]['call'] == 'TWO'



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
