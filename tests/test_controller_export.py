from common.utils import Result
from controller.export import ControllerExportMixin


class FakeExporter:
    def __init__(self, result):
        self.result = result
        self.paths = []
        self.qso_lists = []

    def export_to_adif(self, filepath, qsos=None):
        self.paths.append(filepath)
        self.qso_lists.append(qsos)
        return self.result


class ControllerHarness(ControllerExportMixin):
    def __init__(self, exporter):
        self.qso_manager = object()
        self.settings_manager = object()
        self._exporter = exporter


def test_export_to_adif_delegates_to_exporter_and_returns_result():
    expected = Result(True, data="Export complete")
    exporter = FakeExporter(expected)
    controller = ControllerHarness(exporter)

    result = controller.export_to_adif("journal.adi")

    assert result is expected
    assert exporter.paths == ["journal.adi"]


def test_export_to_adif_returns_exporter_failure():
    expected = Result(False, error="Cannot write file")
    exporter = FakeExporter(expected)
    controller = ControllerHarness(exporter)

    result = controller.export_to_adif("readonly.adi")

    assert result is expected
    assert not result.success
    assert result.error == "Cannot write file"


def test_export_to_adif_converts_unexpected_exception_to_result():
    class BrokenExporter:
        def export_to_adif(self, filepath):
            raise OSError("disk unavailable")

    controller = ControllerHarness(BrokenExporter())

    result = controller.export_to_adif("journal.adi")

    assert not result.success
    assert "disk unavailable" in result.error


def test_export_to_adif_passes_explicit_qso_list_to_exporter():
    expected = Result(True, data="Selected records exported")
    exporter = FakeExporter(expected)
    controller = ControllerHarness(exporter)
    selected = [{"call": "R1BQE"}, {"call": "TEST2"}]

    result = controller.export_to_adif("selected.adi", qsos=selected)

    assert result is expected
    assert exporter.paths == ["selected.adi"]
    assert exporter.qso_lists == [selected]
