from constants import BANDS, MODES, DEFAULT_BAND_INDEX, DEFAULT_MODE_INDEX
from utils import Result
from controller_draft import ControllerDraftMixin


class FakeManager:
    def __init__(self):
        self.editing_index = None
        self.draft = None
        self.saved = []
        self.clear_count = 0
        self.save_result = Result(True)
        self.clear_result = Result(True)

    def is_editing(self):
        return self.editing_index is not None

    def save_draft(self, fields):
        self.saved.append(fields.copy())
        if self.save_result.success:
            self.draft = {"version": 1, "fields": fields.copy()}
        return self.save_result

    def load_draft(self):
        return self.draft

    def clear_draft(self):
        self.clear_count += 1
        if self.clear_result.success:
            self.draft = None
        return self.clear_result


class ControllerHarness(ControllerDraftMixin):
    def __init__(self, manager):
        self.qso_manager = manager


def default_fields(**overrides):
    fields = {
        "call": "",
        "name": "",
        "city": "",
        "qth": "",
        "freq": "",
        "comment": "",
        "rst_received": "59",
        "rst_sent": "59",
        "band": BANDS[DEFAULT_BAND_INDEX],
        "mode": MODES[DEFAULT_MODE_INDEX],
        "date": "2026-10-29",
        "time": "02:00:00",
    }
    fields.update(overrides)
    return fields


def test_is_editing_reports_manager_edit_state():
    manager = FakeManager()
    controller = ControllerHarness(manager)

    assert controller.is_editing() is False
    manager.editing_index = 0
    assert controller.is_editing() is True


def test_save_draft_persists_meaningful_fields():
    manager = FakeManager()
    controller = ControllerHarness(manager)
    fields = default_fields(call="R1BQE", comment="unfinished QSO")

    result = controller.save_draft(fields)

    assert result.success
    assert result.data == {"saved": True}
    assert manager.saved == [fields]
    assert manager.clear_count == 0


def test_save_draft_clears_empty_form_instead_of_persisting_it():
    manager = FakeManager()
    manager.draft = {"version": 1, "fields": {"call": "OLD"}}
    controller = ControllerHarness(manager)

    result = controller.save_draft(default_fields())

    assert result.success
    assert result.data == {"saved": False}
    assert manager.saved == []
    assert manager.clear_count == 1
    assert manager.draft is None


def test_save_draft_refuses_to_overwrite_draft_during_qso_edit():
    manager = FakeManager()
    manager.editing_index = 0
    controller = ControllerHarness(manager)

    result = controller.save_draft(default_fields(call="R1BQE"))

    assert not result.success
    assert manager.saved == []
    assert manager.clear_count == 0


def test_load_and_clear_draft_are_delegated_to_manager():
    manager = FakeManager()
    controller = ControllerHarness(manager)
    fields = default_fields(call="R1BQE")
    manager.draft = {"version": 1, "fields": fields}

    assert controller.load_draft() == manager.draft
    result = controller.clear_draft()

    assert result.success
    assert manager.draft is None
    assert manager.clear_count == 1


def test_save_draft_reports_storage_failure():
    manager = FakeManager()
    manager.save_result = Result(False, error="disk full")
    controller = ControllerHarness(manager)

    result = controller.save_draft(default_fields(call="R1BQE"))

    assert not result.success
    assert result.error == "disk full"
