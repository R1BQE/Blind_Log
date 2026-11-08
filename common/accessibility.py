"""Accessibility helpers for native wxPython controls."""

import wx


_AccessibleBase = getattr(wx, "Accessible", None)


class CheckBoxAccessible(_AccessibleBase if _AccessibleBase is not None else object):
    """Expose wx.CheckBox with the explicit MSAA checkbox role."""

    def __init__(self, window):
        if _AccessibleBase is not None:
            super().__init__(window)

    def GetRole(self, child_id):
        role = getattr(wx, "ROLE_SYSTEM_CHECKBUTTON", None)
        if role is None:
            return wx.ACC_NOT_IMPLEMENTED, 0
        return wx.ACC_OK, role


def install_checkbox_accessibility(control, owner):
    """Keep the native checkbox UI and explicitly announce state changes."""
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
            try:
                notifier = getattr(wx.Accessible, "NotifyEvent", None)
                event_type = getattr(wx, "ACC_EVENT_OBJECT_STATECHANGE", None)
                object_id = getattr(wx, "OBJID_CLIENT", None)
                if notifier is not None and event_type is not None and object_id is not None:
                    notifier(event_type, control, object_id, 0)
            except Exception:
                # The native checkbox still changes its value if MSAA
                # notifications are unavailable on this wxWidgets build.
                pass
            event.Skip()

        control.Bind(wx.EVT_CHECKBOX, announce_state_change)
    except Exception:
        # Never prevent the settings or filter dialog from opening because
        # an accessibility extension is unavailable on a platform.
        return
