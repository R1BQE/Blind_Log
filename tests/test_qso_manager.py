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

    # Проверка базового формата даты/времени
    datetime.strptime(qso['datetime'], '%Y-%m-%d %H:%M')


def test_add_qso_invalid_data(qso_manager):
    result = qso_manager.add_qso({'call': ''})

    assert result.success is False
    assert 'позывной' in result.error.lower()
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
    assert 'индекс' in result.error.lower()
    assert len(qso_manager.qso_list) == 1
