"""MSAA accessibility support for wx.CheckBox controls on Windows."""

import wx


_AccessibleBase = getattr(wx, "Accessible", None)


if _AccessibleBase is not None:
    class CheckBoxAccessible(_AccessibleBase):
        """Expose the checkbox role and read its current state from wx.CheckBox."""

        def __init__(self, control):
            super().__init__(control)
            self._control = control

        def GetRole(self, child_id):
            if child_id != 0:
                return wx.ACC_NOT_IMPLEMENTED, 0
            return wx.ACC_OK, wx.ROLE_SYSTEM_CHECKBUTTON

        def GetState(self, child_id):
            if child_id != 0:
                return wx.ACC_NOT_IMPLEMENTED, 0

            control = self._control
            state = 0
            if control.GetValue():
                state |= getattr(wx, "ACC_STATE_SYSTEM_CHECKED", 0x20)
            if control.IsEnabled():
                state |= getattr(wx, "ACC_STATE_SYSTEM_FOCUSABLE", 0x800)
            else:
                state |= getattr(wx, "ACC_STATE_SYSTEM_UNAVAILABLE", 0x2000000)
            if control.HasFocus():
                state |= getattr(wx, "ACC_STATE_SYSTEM_FOCUSED", 0x1000)
            return wx.ACC_OK, state


def install_checkbox_accessibility(control, owner):
    """Attach a live MSAA checkbox provider and notify clients after toggling."""
    if _AccessibleBase is None or not hasattr(control, "SetAccessible"):
        return

    try:
        provider = CheckBoxAccessible(control)
        control.SetAccessible(provider)

        providers = getattr(owner, "_checkbox_accessible_providers", None)
        if providers is None:
            providers = []
            owner._checkbox_accessible_providers = providers
        providers.append(provider)

        def announce_state_change(event):
            event.Skip()
            try:
                notifier = getattr(wx.Accessible, "NotifyEvent", None)
                event_type = getattr(wx, "ACC_EVENT_OBJECT_STATECHANGE", None)
                object_id = getattr(wx, "OBJID_CLIENT", None)
                if notifier is not None and event_type is not None and object_id is not None:
                    notifier(event_type, control, object_id, 0)
            except Exception:
                pass

        control.Bind(wx.EVT_CHECKBOX, announce_state_change)
    except Exception:
        # Accessibility extensions must never prevent a dialog from opening.
        return
