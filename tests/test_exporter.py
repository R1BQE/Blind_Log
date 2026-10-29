from pathlib import Path


def test_export_to_adif_includes_expected_fields(qso_manager, settings_manager, tmp_path):
    qso_manager.qso_list = [
        {
            'call': 'TEST1',
            'name': 'Ivan Ivanov',
            'city': 'Moscow',
            'qth': 'KN18YV',
            'band': '20m',
            'mode': 'SSB',
            'freq': '14.200',
            'rst_received': '59',
            'rst_sent': '59',
            'comment': 'test comment',
            'datetime': '2025-01-01 12:00:15',
        }
    ]

    from exporter import Exporter

    exporter = Exporter(qso_manager, settings_manager)
    output_file = Path(tmp_path) / 'export_test.adi'

    result = exporter.export_to_adif(str(output_file))

    assert result.success is True
    assert result.error is None
    content = output_file.read_text(encoding='cp1251')

    assert '#   Created:' in content
    assert '<ADIF_VER:5>3.1.7' in content
    assert '<CALL:5>TEST1' in content
    assert '<QSO_DATE:8>20250101' in content
    assert '<TIME_ON:6>120015' in content
    assert '<FREQ:6>14.200' in content
    assert '<MODE:3>SSB' in content
    assert '<RST_SENT:2>59' in content
    assert '<RST_RCVD:2>59' in content
    assert '<GRIDSQUARE:6>KN18YV' in content
    assert '<NAME:11>Ivan Ivanov' in content
    assert '<QTH:6>Moscow' in content
    assert '<COMMENT:12>test comment' in content
    assert '<MY_NAME:13>Test Operator' in content
    assert '<OPERATOR:6>TESTOP' in content
    assert content.count('<MY_NAME:13>Test Operator') == 1
    assert '<EOR>' in content


def test_export_to_adif_formats_datetime_without_seconds(qso_manager, settings_manager, tmp_path):
    qso_manager.qso_list = [
        {
            'call': 'TEST1',
            'name': 'Ivan Ivanov',
            'city': 'Moscow',
            'qth': 'KN18YV',
            'band': '20m',
            'mode': 'SSB',
            'freq': '14.200',
            'rst_received': '59',
            'rst_sent': '59',
            'comment': 'test comment',
            'datetime': '2025-01-01 12:00',
        }
    ]

    from exporter import Exporter

    exporter = Exporter(qso_manager, settings_manager)
    output_file = Path(tmp_path) / 'datetime_export.adi'

    result = exporter.export_to_adif(str(output_file))

    assert result.success is True
    assert result.error is None
    content = output_file.read_text(encoding='cp1251')

    assert '<QSO_DATE:8>20250101' in content
    assert '<TIME_ON:6>120000' in content


def test_export_to_adif_handles_empty_qso_list(settings_manager, tmp_path):
    from exporter import Exporter
    from qso_manager import QSOManager
    import utils

    settings_manager.settings['use_qrz_lookup'] = '0'
    class EmptyQSOManager:
        def __init__(self):
            self.qso_list = []
            self.auto_temp = False
        def get_qso_list(self):
            return self.qso_list

    exporter = Exporter(EmptyQSOManager(), settings_manager)
    output_file = Path(tmp_path) / 'empty_export.adi'

    result = exporter.export_to_adif(str(output_file))

    assert result.success is True
    assert result.error is None
    content = output_file.read_text(encoding='cp1251')
    assert '#   Created:' in content
    assert '<ADIF_VER:5>3.1.7' in content
    assert '<CALL:' not in content
    assert '<EOR>' not in content



def test_utf8_adif_round_trip_preserves_cyrillic(qso_manager, settings_manager, tmp_path):
    from exporter import Exporter
    from importer import import_adif_file

    qso_manager.qso_list = [{
        "call": "R1BQE",
        "name": "Иван",
        "city": "Санкт-Петербург",
        "qth": "KO59",
        "band": "2m",
        "mode": "FM",
        "freq": "145.500",
        "rst_received": "59",
        "rst_sent": "59",
        "comment": "Проверка кириллицы",
        "datetime": "2026-10-29 02:00:00",
    }]
    path = Path(tmp_path) / "cyrillic.adi"
    result = Exporter(qso_manager, settings_manager).export_to_adif(str(path))
    assert result.success is True
    text = path.read_text(encoding="utf-8")
    assert "CHARSET" in text
    assert "Иван" in text

    imported = import_adif_file(str(path))
    assert imported.success is True
    qso = imported.data["qsos"][0]
    assert qso["name"] == "Иван"
    assert qso["city"] == "Санкт-Петербург"
    assert qso["comment"] == "Проверка кириллицы"
