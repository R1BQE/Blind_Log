from utils import Result
from controller_qso_actions import ControllerQSOActionsMixin


class FakeManager:
    def __init__(self, result=None, qsos=None):
        self.result = result or Result(True, data={"call": "R1BQE"})
        self.qsos = qsos or []
        self.editing_index = None
        self.calls = []

    def add_qso(self, data):
        self.calls.append(("add_qso", data))
        return self.result

    def get_qso_count(self):
        return len(self.qsos)

    def get_qso(self, index):
        return self.qsos[index].copy() if 0 <= index < len(self.qsos) else None

    def delete_qso(self, index):
        self.calls.append(("delete_qso", index))
        self.qsos.pop(index)
        return Result(True)

    def begin_edit(self, index):
        self.editing_index = index
        return Result(True)

    def cancel_edit(self):
        self.editing_index = None


class FakeBridge:
    def __init__(self, values=None):
        self.values = values or {}
        self.events = []

    def get_control_value(self, name):
        return self.values.get(name, "")

    def clear_form(self):
        self.events.append(("clear_form",))

    def update_journal_display(self):
        self.events.append(("update_journal_display",))

    def set_focus(self, name):
        self.events.append(("set_focus", name))

    def switch_tab(self, index):
        self.events.append(("switch_tab", index))

    def populate_form(self, qso):
        self.events.append(("populate_form", qso))


class ControllerHarness(ControllerQSOActionsMixin):
    def __init__(self, manager, bridge=None):
        self.qso_manager = manager
        self.gui_bridge = bridge
        self.notifications = []
        self.errors = []

    def _notify_success(self, message):
        self.notifications.append(message)

    def _notify_error(self, title, message):
        self.errors.append((title, message))


def test_add_qso_from_gui_reads_fields_and_updates_accessible_ui():
    manager = FakeManager()
    bridge = FakeBridge({
        "call": "r1bqe",
        "name": "Иван",
        "date": "2026-10-29",
        "time": "02:30",
        "freq": "145.500",
        "mode": "FM",
    })
    controller = ControllerHarness(manager, bridge)

    result = controller.add_qso_from_gui()

    assert result.success
    assert manager.calls[0][0] == "add_qso"
    data = manager.calls[0][1]
    assert data["call"] == "r1bqe"
    assert data["name"] == "Иван"
    assert data["datetime"] == "2026-10-29 02:30"
    assert data["freq"] == "145.500"
    assert bridge.events == [
        ("clear_form",),
        ("update_journal_display",),
        ("set_focus", "call"),
    ]
    assert len(controller.notifications) == 1
    assert controller.errors == []


def test_add_qso_from_gui_reports_validation_failure():
    manager = FakeManager(Result(False, error="Invalid callsign"))
    controller = ControllerHarness(manager, FakeBridge({"call": ""}))

    result = controller.add_qso_from_gui()

    assert not result.success
    assert controller.errors
    assert "Invalid callsign" in controller.errors[0][1]
    assert controller.notifications == []


def test_delete_qso_rejects_invalid_index_without_mutating_journal():
    manager = FakeManager(qsos=[{"call": "R1BQE"}])
    controller = ControllerHarness(manager)

    result = controller.delete_qso(5)

    assert not result.success
    assert manager.qsos == [{"call": "R1BQE"}]
    assert manager.calls == []
    assert controller.errors


def test_load_qso_for_edit_populates_form_and_starts_edit_mode():
    qso = {"call": "R1BQE", "datetime": "2026-10-29 02:00"}
    manager = FakeManager(qsos=[qso])
    bridge = FakeBridge()
    controller = ControllerHarness(manager, bridge)

    assert controller.load_qso_for_edit(0) is True

    assert manager.editing_index == 0
    assert bridge.events == [
        ("switch_tab", 0),
        ("populate_form", qso),
        ("set_focus", "call"),
    ]


def test_load_qso_for_edit_rejects_invalid_index():
    manager = FakeManager()
    controller = ControllerHarness(manager)

    assert controller.load_qso_for_edit(0) is False
    assert controller.errors
