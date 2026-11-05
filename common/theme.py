"""Application color themes for wxPython windows."""

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


def apply_theme(window, theme=THEME_SYSTEM):
    """Apply a theme recursively to a window and its current child controls."""
    resolved = resolve_theme(theme)

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

    def apply_to_child(child):
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

    apply_to_child(window)
    return resolved
