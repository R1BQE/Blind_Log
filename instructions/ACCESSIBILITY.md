# ACCESSIBILITY.md

Blind_Log is designed for keyboard-first use by visually impaired operators.

- All primary actions must be reachable from the keyboard.
- Focus order must be predictable in the main window, tabs and dialogs.
- Switching the main tabs must not forcibly move focus into a form field or the journal list.
- Dialogs must have meaningful labels, predictable Tab navigation and Escape behavior where supported.
- Do not introduce mouse-only actions.
- Preserve native Windows checkbox behavior and accessibility roles. Never custom-color native checkboxes.
- Use the accessibility layer for screen-reader announcements; announce meaningful state changes without unnecessary repetition.
- Date/time pickers remain native wxPython controls. The active segment is announced on focus; Left/Right move between segments and Up/Down change the selected segment.
- Use `wx.CallAfter` for UI updates scheduled from background operations.
- Verify keyboard behavior, accessible role/state and actual NVDA output after GUI changes.
- Test light, dark and system themes to ensure theming does not damage control accessibility.
