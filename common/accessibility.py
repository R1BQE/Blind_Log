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
            role = getattr(wx, "ROLE_SYSTEM_CHECKBUTTON", None)
            if role is None:
                return wx.ACC_NOT_IMPLEMENTED, 0
            return wx.ACC_OK, role

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



if _AccessibleBase is not None:
    class SettingsGroupAccessible(_AccessibleBase):
        """Expose a settings container as a named MSAA grouping object."""

        def __init__(self, control, label):
            super().__init__(control)
            self._label = label

        def GetName(self, child_id):
            if child_id == 0:
                return wx.ACC_OK, self._label
            return wx.ACC_NOT_IMPLEMENTED, ""

        def GetRole(self, child_id):
            if child_id != 0:
                return wx.ACC_NOT_IMPLEMENTED, 0
            role = getattr(wx, "ROLE_SYSTEM_GROUPING", 0x14)
            return wx.ACC_OK, role


    class DecorativeStaticBoxAccessible(_AccessibleBase):
        """Keep the native frame visible while hiding its duplicate MSAA node."""

        def __init__(self, control):
            super().__init__(control)

        def GetName(self, child_id):
            if child_id == 0:
                return wx.ACC_OK, ""
            return wx.ACC_NOT_IMPLEMENTED, ""

        def GetRole(self, child_id):
            if child_id == 0:
                return wx.ACC_OK, getattr(wx, "ROLE_SYSTEM_PANE", 0x10)
            return wx.ACC_NOT_IMPLEMENTED, 0

        def GetState(self, child_id):
            if child_id == 0:
                invisible = getattr(wx, "ACC_STATE_SYSTEM_INVISIBLE", 0x8000)
                return wx.ACC_OK, invisible
            return wx.ACC_NOT_IMPLEMENTED, 0


def install_settings_group_accessibility(panel, static_box, label, owner):
    """Give a settings panel a named grouping role and hide its decorative frame."""
    if _AccessibleBase is None or not hasattr(panel, "SetAccessible"):
        return

    try:
        group_provider = SettingsGroupAccessible(panel, label)
        panel.SetAccessible(group_provider)

        frame_provider = DecorativeStaticBoxAccessible(static_box)
        static_box.SetAccessible(frame_provider)

        providers = getattr(owner, "_settings_group_accessible_providers", None)
        if providers is None:
            providers = []
            owner._settings_group_accessible_providers = providers
        providers.extend((group_provider, frame_provider))
    except Exception:
        # Accessibility metadata must never prevent settings from opening.
        return

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
