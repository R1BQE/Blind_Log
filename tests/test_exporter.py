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
            'datetime': '2025-01-01 12:00',
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
    assert '<ADIF_VER:3>2.0' in content
    assert '<CALL:5>TEST1' in content
    assert '<QSO_DATE:8>20250101' in content
    assert '<TIME_ON:4>1200' in content
    assert '<FREQ:6>14.200' in content
    assert '<MODE:3>SSB' in content
    assert '<RST_SENT:2>59' in content
    assert '<RST_RCVD:2>59' in content
    assert '<GRIDSQUARE:6>KN18YV' in content
    assert '<NAME:11>Ivan Ivanov' in content
    assert '<QTH:6>Moscow' in content
    assert '<COMMENT:12>test comment' in content
    assert '<MY_NAME:13>Test Operator' in content
    assert '<EOR>' in content


def test_export_to_adif_handles_empty_qso_list(settings_manager, tmp_path):
    from exporter import Exporter
    from qso_manager import QSOManager
    import utils

    settings_manager.settings['use_qrz_lookup'] = '0'
    exporter = Exporter(type('EmptyQSOManager', (), {'qso_list': [], 'auto_temp': False})(), settings_manager)
    output_file = Path(tmp_path) / 'empty_export.adi'

    result = exporter.export_to_adif(str(output_file))

    assert result.success is True
    assert result.error is None
    content = output_file.read_text(encoding='cp1251')
    assert '#   Created:' in content
    assert '<ADIF_VER:3>2.0' in content
    assert '<CALL:' not in content
    assert '<EOR>' not in content
