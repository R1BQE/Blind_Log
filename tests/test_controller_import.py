from utils import Result
import controller_import


class FakeManager:
    def __init__(self, result=None):
        self.result = result if result is not None else Result(True, data={"imported": 1, "skipped": 0, "total": 1})
        self.calls = []

    def import_qso_list(self, qsos, mode="replace"):
        self.calls.append((qsos, mode))
        return self.result


class FakeBridge:
    def __init__(self, fail=False):
        self.events = []
        self.fail = fail

    def update_journal_display(self):
        self.events.append("update")
        if self.fail:
            raise RuntimeError("UI unavailable")


class ControllerHarness(controller_import.ControllerImportMixin):
    def __init__(self, manager, bridge=None):
        self.qso_manager = manager
        self.gui_bridge = bridge
        self.notifications = []
        self.errors = []

    def _notify_success(self, message):
        self.notifications.append(message)

    def _notify_error(self, title, message):
        self.errors.append((title, message))


def test_import_adif_file_passes_parsed_records_and_mode_to_manager(monkeypatch):
    qsos = [{"call": "R1BQE", "datetime": "2026-10-29 02:00"}]
    monkeypatch.setattr(
        controller_import,
        "_do_import",
        lambda filepath: Result(True, data={"qsos": qsos}),
    )
    manager = FakeManager()
    bridge = FakeBridge()
    controller = ControllerHarness(manager, bridge)

    result = controller.import_adif_file("log.adi", mode="append")

    assert result.success
    assert manager.calls == [(qsos, "append")]
    assert bridge.events == ["update"]
    assert len(controller.notifications) == 1


def test_import_adif_file_returns_parser_error_without_mutating_journal(monkeypatch):
    parser_result = Result(False, error="Malformed ADIF")
    monkeypatch.setattr(controller_import, "_do_import", lambda _: parser_result)
    manager = FakeManager()
    controller = ControllerHarness(manager)

    result = controller.import_adif_file("bad.adi")

    assert result is parser_result
    assert manager.calls == []


def test_import_adif_file_rejects_empty_parsed_file(monkeypatch):
    monkeypatch.setattr(
        controller_import,
        "_do_import",
        lambda _: Result(True, data={"qsos": []}),
    )
    manager = FakeManager()
    controller = ControllerHarness(manager)

    result = controller.import_adif_file("empty.adi")

    assert not result.success
    assert manager.calls == []


def test_import_adif_file_handles_missing_dependency(monkeypatch):
    def raise_missing_dependency(_):
        raise ModuleNotFoundError("adif-io")

    monkeypatch.setattr(controller_import, "_do_import", raise_missing_dependency)
    manager = FakeManager()
    controller = ControllerHarness(manager)

    result = controller.import_adif_file("log.adi")

    assert not result.success
    assert "Importer module not available" in result.error
    assert manager.calls == []


def test_import_adif_file_keeps_success_when_ui_refresh_fails(monkeypatch):
    qsos = [{"call": "R1BQE"}]
    monkeypatch.setattr(
        controller_import,
        "_do_import",
        lambda _: Result(True, data={"qsos": qsos}),
    )
    manager = FakeManager()
    bridge = FakeBridge(fail=True)
    controller = ControllerHarness(manager, bridge)

    result = controller.import_adif_file("log.adi")

    assert result.success
    assert manager.calls == [(qsos, "replace")]
    assert len(controller.notifications) == 1



def test_import_adif_file_surfaces_manager_failure_to_user(monkeypatch):
    qsos = [{"call": "R1BQE"}]
    monkeypatch.setattr(
        controller_import,
        "_do_import",
        lambda _: Result(True, data={"qsos": qsos}),
    )
    manager = FakeManager(Result(False, error="Finish or cancel the current QSO edit"))
    controller = ControllerHarness(manager)

    result = controller.import_adif_file("log.adi")

    assert not result.success
    assert controller.errors == [("Error", "Finish or cancel the current QSO edit")]
    assert controller.notifications == []
