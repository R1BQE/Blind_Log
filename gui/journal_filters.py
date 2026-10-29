"""Accessible search, sorting and filtering helpers for the journal."""

from datetime import datetime
import wx

from common.constants import BANDS, MODES
from localization.i18n import tr

TEXT_FILTERS = (
    ("call", "label.callsign"), ("name", "label.name"),
    ("city", "label.city"), ("qth", "label.qth"),
)
SORT_FIELDS = (
    ("datetime", "journal.datetime"), ("call", "journal.callsign"),
    ("name", "journal.name"), ("city", "journal.city"), ("qth", "journal.qth"),
    ("band", "journal.band"), ("mode", "journal.mode"), ("freq", "journal.freq"),
    ("rst_received", "journal.rst_received"), ("rst_sent", "journal.rst_sent"),
)


def empty_filter_state():
    return {
        "enabled": {key: False for key, _ in TEXT_FILTERS},
        "values": {key: "" for key, _ in TEXT_FILTERS},
        "bands": [], "modes": [],
        "date_enabled": False, "date": "",
        "date_range_enabled": False, "date_from": "", "date_to": "",
        "time_enabled": False, "time": "",
        "time_range_enabled": False, "time_from": "", "time_to": "",
    }


def _copy_state(source):
    state = empty_filter_state()
    state["enabled"].update(source.get("enabled", {}))
    state["values"].update(source.get("values", {}))
    state["bands"] = list(source.get("bands", []))
    state["modes"] = list(source.get("modes", []))
    for key in ("date_enabled", "date", "date_range_enabled", "date_from", "date_to",
                "time_enabled", "time", "time_range_enabled", "time_from", "time_to"):
        if key in source:
            state[key] = source[key]
    return state


def parse_qso_datetime(qso):
    raw = str(qso.get("datetime", "") or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                pass
    return None


def _parse_time(value):
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(str(value).strip(), fmt).time()
        except ValueError:
            pass
    raise ValueError("Time must be HH:MM or HH:MM:SS")


def filter_qsos(qsos, query="", filters=None):
    filters = filters or empty_filter_state()
    query = (query or "").strip().casefold()
    bands, modes = set(filters.get("bands", [])), set(filters.get("modes", []))
    result = []
    for qso in qsos:
        if query and not any(query in str(value or "").casefold() for value in qso.values()):
            continue
        rejected = False
        for key, enabled in filters.get("enabled", {}).items():
            if enabled:
                value = str(filters.get("values", {}).get(key, "") or "").strip().casefold()
                if not value or value not in str(qso.get(key, "") or "").casefold():
                    rejected = True
                    break
        if rejected:
            continue
        if bands and str(qso.get("band", "") or "") not in bands:
            continue
        if modes and str(qso.get("mode", "") or "") not in modes:
            continue
        dt = parse_qso_datetime(qso)
        if filters.get("date_enabled"):
            try:
                expected = datetime.strptime(filters["date"], "%d.%m.%Y").date()
            except ValueError:
                continue
            if dt is None or dt.date() != expected:
                continue
        if filters.get("date_range_enabled"):
            try:
                start = datetime.strptime(filters["date_from"], "%d.%m.%Y").date()
                end = datetime.strptime(filters["date_to"], "%d.%m.%Y").date()
            except ValueError:
                continue
            if start > end or dt is None or not start <= dt.date() <= end:
                continue
        if filters.get("time_enabled"):
            try:
                expected = _parse_time(filters["time"])
            except ValueError:
                continue
            if dt is None or dt.time() != expected:
                continue
        if filters.get("time_range_enabled"):
            try:
                start, end = _parse_time(filters["time_from"]), _parse_time(filters["time_to"])
            except ValueError:
                continue
            if dt is None:
                continue
            current = dt.time()
            matches = start <= current <= end if start <= end else current >= start or current <= end
            if not matches:
                continue
        result.append(qso)
    return result


def sort_qsos(qsos, sort_key="datetime_desc"):
    descending = sort_key.endswith("_desc")
    field = sort_key[:-5] if descending else sort_key[:-4]
    if field not in {key for key, _ in SORT_FIELDS}:
        field, descending = "datetime", True

    def value_for(qso):
        value = qso.get(field, "")
        text = str(value or "").strip()
        if not text:
            return None
        if field == "datetime":
            return parse_qso_datetime(qso)
        if field == "freq":
            try:
                return float(text.replace(",", "."))
            except ValueError:
                return None
        if field in ("rst_received", "rst_sent"):
            try:
                return int(text)
            except ValueError:
                return None
        if field == "band":
            try:
                return (0, BANDS.index(text))
            except ValueError:
                return (1, text.casefold())
        return text.casefold()

    present, missing = [], []
    for qso in qsos:
        value = value_for(qso)
        (missing if value is None else present).append((qso, value) if value is not None else qso)
    present.sort(key=lambda item: item[1], reverse=descending)
    return [item[0] for item in present] + missing


class JournalFilterDialog(wx.Dialog):
    """Accessible keyboard-driven filter dialog."""

    def __init__(self, parent, current=None):
        super().__init__(parent, title=tr("journal.filters.title"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._initial = _copy_state(current or empty_filter_state())
        self._checks, self._fields, self._field_labels = {}, {}, {}
        self._band_checks, self._mode_checks = {}, {}
        outer = wx.BoxSizer(wx.VERTICAL)
        self.scroller = wx.ScrolledWindow(self, style=wx.VSCROLL | wx.TAB_TRAVERSAL)
        self.scroller.SetScrollRate(0, 15)
        self.body = wx.BoxSizer(wx.VERTICAL)

        for key, label_key in TEXT_FILTERS:
            self._add_text_filter(key, tr(label_key))
        self.body.Add(wx.StaticText(self.scroller, label=tr("journal.filters.bands")), 0, wx.ALL, 5)
        for band in BANDS:
            check = wx.CheckBox(self.scroller, label=band)
            check.SetValue(band in self._initial["bands"])
            self._band_checks[band] = check
            self.body.Add(check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.body.Add(wx.StaticText(self.scroller, label=tr("journal.filters.modes")), 0, wx.ALL, 5)
        for mode in MODES:
            check = wx.CheckBox(self.scroller, label=mode)
            check.SetValue(mode in self._initial["modes"])
            self._mode_checks[mode] = check
            self.body.Add(check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        self._add_single_filter("date_enabled", "date", tr("journal.filters.date"))
        self._add_range_filter("date_range_enabled", "date_from", "date_to", tr("journal.filters.date_range"))
        self._add_single_filter("time_enabled", "time", tr("journal.filters.time"))
        self._add_range_filter("time_range_enabled", "time_from", "time_to", tr("journal.filters.time_range"))

        self.scroller.SetSizer(self.body)
        self.body.Fit(self.scroller)
        outer.Add(self.scroller, 1, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.reset_button = wx.Button(self, label=tr("journal.filters.reset"))
        self.apply_button = wx.Button(self, label=tr("journal.filters.apply"), id=wx.ID_OK)
        self.cancel_button = wx.Button(self, label=tr("dialog.cancel"), id=wx.ID_CANCEL)
        buttons.Add(self.reset_button, 0, wx.ALL, 5)
        buttons.AddStretchSpacer()
        buttons.Add(self.apply_button, 0, wx.ALL, 5)
        buttons.Add(self.cancel_button, 0, wx.ALL, 5)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 3)
        self.SetSizerAndFit(outer)
        self.SetMinSize((520, 560))
        self.reset_button.Bind(wx.EVT_BUTTON, self._reset)
        self.apply_button.Bind(wx.EVT_BUTTON, self._apply)
        self.cancel_button.Bind(wx.EVT_BUTTON, lambda event: self.EndModal(wx.ID_CANCEL))
        self.Bind(wx.EVT_CHAR_HOOK, self._char_hook)
        self._sync_visibility()

    def _add_text_filter(self, key, label):
        row = wx.BoxSizer(wx.VERTICAL)
        check = wx.CheckBox(self.scroller, label=label)
        check.SetValue(self._initial["enabled"].get(key, False))
        field_label = wx.StaticText(self.scroller, label=label + ":")
        field = wx.TextCtrl(self.scroller, value=self._initial["values"].get(key, ""))
        field.SetHint(_filter_hint(key))
        self._checks[key], self._fields[key] = check, field
        row.Add(check, 0, wx.ALL, 4)
        row.Add(field_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        row.Add(field, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self._field_labels[key] = field_label
        self.body.Add(row, 0, wx.EXPAND | wx.ALL, 2)
        check.Bind(wx.EVT_CHECKBOX, lambda event, k=key: self._toggle_text(k))

    def _add_single_filter(self, enabled_key, field_key, label):
        row = wx.BoxSizer(wx.VERTICAL)
        check = wx.CheckBox(self.scroller, label=label)
        check.SetValue(bool(self._initial.get(enabled_key)))
        field_label = wx.StaticText(self.scroller, label=label + ":")
        field = wx.TextCtrl(self.scroller, value=str(self._initial.get(field_key, "")))
        field.SetHint(_filter_hint(field_key))
        self._checks[enabled_key], self._fields[field_key] = check, field
        self._field_labels[field_key] = field_label
        row.Add(check, 0, wx.ALL, 4)
        row.Add(field_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        row.Add(field, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.body.Add(row, 0, wx.EXPAND | wx.ALL, 2)
        check.Bind(wx.EVT_CHECKBOX, lambda event, k=enabled_key: self._toggle_date_time(k))

    def _add_range_filter(self, enabled_key, from_key, to_key, label):
        row = wx.BoxSizer(wx.VERTICAL)
        check = wx.CheckBox(self.scroller, label=label)
        check.SetValue(bool(self._initial.get(enabled_key)))
        from_label = wx.StaticText(self.scroller, label=tr("journal.filters.from"))
        from_field = wx.TextCtrl(self.scroller, value=str(self._initial.get(from_key, "")))
        to_label = wx.StaticText(self.scroller, label=tr("journal.filters.to"))
        to_field = wx.TextCtrl(self.scroller, value=str(self._initial.get(to_key, "")))
        self._checks[enabled_key] = check
        self._fields[from_key], self._fields[to_key] = from_field, to_field
        self._field_labels[from_key], self._field_labels[to_key] = from_label, to_label
        row.Add(check, 0, wx.ALL, 4)
        row.Add(from_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        from_field.SetHint(_filter_hint(from_key))
        row.Add(from_field, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        row.Add(to_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        to_field.SetHint(_filter_hint(to_key))
        row.Add(to_field, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.body.Add(row, 0, wx.EXPAND | wx.ALL, 2)
        check.Bind(wx.EVT_CHECKBOX, lambda event, k=enabled_key: self._toggle_date_time(k))

    def _clear_fields(self, enabled_key):
        mapping = {
            "date_enabled": ("date",), "date_range_enabled": ("date_from", "date_to"),
            "time_enabled": ("time",), "time_range_enabled": ("time_from", "time_to"),
        }
        for key in mapping.get(enabled_key, ()):
            self._fields[key].SetValue("")

    def _toggle_text(self, key):
        if not self._checks[key].GetValue():
            self._fields[key].SetValue("")
        self._sync_visibility()

    def _toggle_date_time(self, key):
        if self._checks[key].GetValue():
            other = {
                "date_enabled": "date_range_enabled", "date_range_enabled": "date_enabled",
                "time_enabled": "time_range_enabled", "time_range_enabled": "time_enabled",
            }[key]
            self._checks[other].SetValue(False)
            self._clear_fields(other)
        else:
            self._clear_fields(key)
        self._sync_visibility()

    def _sync_visibility(self):
        for key, check in self._checks.items():
            if key in self._fields:
                self._fields[key].Show(check.GetValue())
        for key, field in self._fields.items():
            enabled_key = {
                "date": "date_enabled", "date_from": "date_range_enabled", "date_to": "date_range_enabled",
                "time": "time_enabled", "time_from": "time_range_enabled", "time_to": "time_range_enabled",
            }.get(key)
            visible = self._checks[enabled_key].GetValue() if enabled_key else self._checks[key].GetValue()
            field.Show(visible)
            if key in self._field_labels:
                self._field_labels[key].Show(visible)
        self.Layout()
        self.scroller.Layout()
        self.body.Layout()
        self.scroller.FitInside()

    def _reset(self, event):
        for check in self._checks.values():
            check.SetValue(False)
        for field in self._fields.values():
            field.SetValue("")
        for check in self._band_checks.values():
            check.SetValue(False)
        for check in self._mode_checks.values():
            check.SetValue(False)
        self._sync_visibility()

    def _warn_focus(self, message, field_key):
        wx.MessageBox(message, tr("journal.filters.warning_title"), wx.OK | wx.ICON_WARNING, self)
        self._fields[field_key].SetFocus()

    def _apply(self, event):
        state = self.get_filter_state()
        labels = dict(TEXT_FILTERS)
        for key, enabled in state["enabled"].items():
            if enabled and not state["values"].get(key, "").strip():
                self._warn_focus(tr("journal.filters.required").format(field=tr(labels[key])), key)
                return
        for enabled_key, field_key, label in (
            ("date_enabled", "date", tr("journal.filters.date")),
            ("date_range_enabled", "date_from", tr("journal.filters.date_range")),
            ("time_enabled", "time", tr("journal.filters.time")),
            ("time_range_enabled", "time_from", tr("journal.filters.time_range")),
        ):
            if state[enabled_key] and not state[field_key].strip():
                self._warn_focus(tr("journal.filters.required").format(field=label), field_key)
                return
        if state["date_range_enabled"]:
            for key in ("date_from", "date_to"):
                if not state[key].strip():
                    self._warn_focus(tr("journal.filters.required").format(
                        field=tr("journal.filters.date_range") + " " + tr("journal.filters.from" if key == "date_from" else "journal.filters.to")
                    ), key)
                    return
        if state["time_range_enabled"]:
            for key in ("time_from", "time_to"):
                if not state[key].strip():
                    self._warn_focus(tr("journal.filters.required").format(
                        field=tr("journal.filters.time_range") + " " + tr("journal.filters.from" if key == "time_from" else "journal.filters.to")
                    ), key)
                    return
        try:
            if state["date_enabled"]:
                datetime.strptime(state["date"], "%d.%m.%Y")
            if state["date_range_enabled"]:
                start = datetime.strptime(state["date_from"], "%d.%m.%Y").date()
                end = datetime.strptime(state["date_to"], "%d.%m.%Y").date()
                if start > end:
                    self._warn_focus(tr("journal.filters.date_order"), "date_from")
                    return
            if state["time_enabled"]:
                _parse_time(state["time"])
            if state["time_range_enabled"]:
                _parse_time(state["time_from"])
                _parse_time(state["time_to"])
        except ValueError as error:
            message = tr("journal.filters.invalid_time") if "Time" in str(error) else tr("journal.filters.invalid_date")
            field = next((key for key in ("date", "date_from", "date_to", "time", "time_from", "time_to")
                          if state.get(key) and not _valid_filter_value(key, state[key])), "date")
            self._warn_focus(message, field)
            return
        self._result_state = state
        self.EndModal(wx.ID_OK)

    def _char_hook(self, event):
        if event.AltDown():
            code = event.GetKeyCode()
            if code in (ord("R"), ord("r")):
                self._reset(None)
                return
            if code in (ord("A"), ord("a")):
                self._apply(None)
                return
            if code in (ord("C"), ord("c")):
                self.EndModal(wx.ID_CANCEL)
                return
        event.Skip()

    def get_filter_state(self):
        state = empty_filter_state()
        for key, _ in TEXT_FILTERS:
            enabled = self._checks[key].GetValue()
            state["enabled"][key] = enabled
            state["values"][key] = self._fields[key].GetValue().strip() if enabled else ""
        state["bands"] = [key for key, check in self._band_checks.items() if check.GetValue()]
        state["modes"] = [key for key, check in self._mode_checks.items() if check.GetValue()]
        for key in ("date_enabled", "date_range_enabled", "time_enabled", "time_range_enabled"):
            state[key] = self._checks[key].GetValue()
        for key, field in self._fields.items():
            if key not in state["values"]:
                state[key] = field.GetValue().strip() if _field_is_enabled(key, self._checks) else ""
        return state

    def get_result_state(self):
        return getattr(self, "_result_state", self._initial)


def _field_is_enabled(key, checks):
    return {
        "date": checks["date_enabled"].GetValue(),
        "date_from": checks["date_range_enabled"].GetValue(),
        "date_to": checks["date_range_enabled"].GetValue(),
        "time": checks["time_enabled"].GetValue(),
        "time_from": checks["time_range_enabled"].GetValue(),
        "time_to": checks["time_range_enabled"].GetValue(),
    }.get(key, True)


def _valid_filter_value(key, value):
    try:
        if key.startswith("date"):
            datetime.strptime(value, "%d.%m.%Y")
        elif key.startswith("time"):
            _parse_time(value)
        else:
            return bool(value.strip())
        return True
    except ValueError:
        return False


def _filter_hint(key):
    examples = {
        "call": "Например: R1BQE или R1",
        "name": "Например: Алексей",
        "city": "Например: Альметьевск",
        "qth": "Например: KO59",
        "date": "Например: 29.10.2026",
        "date_from": "Например: 20.09.2026",
        "date_to": "Например: 30.09.2026",
        "time": "Например: 14:30 или 14:30:00",
        "time_from": "Например: 08:00",
        "time_to": "Например: 18:30:00",
    }
    return tr("journal.filters.example").format(example=examples.get(key, ""))
