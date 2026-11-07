"""Application color themes for wxPython windows."""

import sys

import wx


THEME_SYSTEM = "system"
THEME_LIGHT = "light"
THEME_DARK = "dark"


def _system_prefers_dark():
    """Detect the operating-system appearance, with a color-based fallback."""
    try:
        appearance = wx.SystemSettings.GetAppearance()
        if hasattr(appearance, "IsDark"):
            return bool(appearance.IsDark())
    except Exception:
        pass

    try:
        color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        luminance = (
            0.2126 * color.Red()
            + 0.7152 * color.Green()
            + 0.0722 * color.Blue()
        )
        return luminance < 128
    except Exception:
        return False


def resolve_theme(theme):
    """Resolve system/light/dark to the palette that should be displayed."""
    if theme == THEME_DARK:
        return THEME_DARK
    if theme == THEME_LIGHT:
        return THEME_LIGHT
    return THEME_DARK if _system_prefers_dark() else THEME_LIGHT


def _apply_windows_titlebar_theme(window, resolved):
    """Match the native Windows title bar to the selected application theme."""
    if sys.platform != "win32":
        return

    try:
        import ctypes

        hwnd = ctypes.c_void_p(int(window.GetHandle()))
        dark_mode = ctypes.c_int(1 if resolved == THEME_DARK else 0)
        dwmapi = ctypes.WinDLL("dwmapi")
        set_attribute = dwmapi.DwmSetWindowAttribute
        set_attribute.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_uint,
        ]
        set_attribute.restype = ctypes.c_long

        # Windows 11 uses attribute 20; earlier supported Windows 10 builds
        # use 19. Unsupported versions simply keep their native title bar.
        for attribute in (20, 19):
            result = set_attribute(
                hwnd,
                attribute,
                ctypes.byref(dark_mode),
                ctypes.sizeof(dark_mode),
            )
            if result == 0:
                break
    except Exception:
        # The color theme must remain usable if DWM customization is absent.
        pass


def apply_theme(window, theme=THEME_SYSTEM):
    """Apply a theme recursively while avoiding intermediate repaint flashes."""
    resolved = resolve_theme(theme)
    _apply_windows_titlebar_theme(window, resolved)

    if resolved == THEME_DARK:
        window_bg = wx.Colour(32, 33, 36)
        text_fg = wx.Colour(232, 234, 237)
        control_bg = wx.Colour(48, 49, 52)
        control_fg = wx.Colour(241, 243, 244)
        button_bg = wx.Colour(60, 64, 67)
    else:
        window_bg = wx.Colour(250, 250, 250)
        text_fg = wx.Colour(32, 33, 33)
        control_bg = wx.Colour(255, 255, 255)
        control_fg = wx.Colour(32, 33, 33)
        button_bg = wx.Colour(240, 240, 240)

    control_types = tuple(
        cls for cls in (
            getattr(wx, "TextCtrl", None),
            getattr(wx, "ListCtrl", None),
            getattr(wx, "Choice", None),
            getattr(wx, "ComboBox", None),
            getattr(wx, "SpinCtrl", None),
            getattr(wx, "CheckBox", None),
            getattr(wx, "RadioButton", None),
            getattr(wx, "RadioBox", None),
        ) if isinstance(cls, type)
    )
    button_type = getattr(wx, "Button", None)

    # Freeze the top-level window before changing child colours. Without this,
    # Windows can paint newly-created controls in their default light palette
    # between individual SetBackgroundColour calls, producing a white flash.
    frozen = False
    try:
        window.Freeze()
        frozen = True
    except Exception:
        # Some native windows do not support Freeze; theming must still work.
        pass

    def apply_to_child(child):
        is_checkbox = isinstance(child, wx.CheckBox)

        if is_checkbox:
            # Keep the native checkbox background and renderer untouched.
            # Set only the label foreground so it remains readable on the
            # dark parent surface. Avoid setting its background: on wxMSW
            # that can replace native checkbox rendering and harm NVDA role
            # exposure and keyboard toggle behavior.
            try:
                child.SetForegroundColour(text_fg)
                child.Refresh()
            except Exception:
                pass
        else:
            try:
                child.SetForegroundColour(text_fg)
                if control_types and isinstance(child, control_types):
                    child.SetBackgroundColour(control_bg)
                    child.SetForegroundColour(control_fg)
                elif button_type and isinstance(child, button_type):
                    child.SetBackgroundColour(button_bg)
                else:
                    child.SetBackgroundColour(window_bg)
                child.Refresh()
            except Exception:
                pass

        try:
            for descendant in child.GetChildren():
                apply_to_child(descendant)
        except Exception:
            pass

    try:
        apply_to_child(window)

        # A wx.Frame status bar is a native child managed separately from the
        # regular window hierarchy on some platforms, so theme it explicitly.
        try:
            status_bar = window.GetStatusBar()
            if status_bar:
                status_bar.SetBackgroundColour(window_bg)
                status_bar.SetForegroundColour(text_fg)
                status_bar.Refresh()
        except Exception:
            # Not every dialog/frame has a status bar, and some native ports
            # do not allow its colours to be customized.
            pass
    finally:
        if frozen:
            try:
                window.Thaw()
                window.Refresh()
                window.Update()
            except Exception:
                pass

    return resolved
