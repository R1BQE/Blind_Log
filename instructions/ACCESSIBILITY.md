# ACCESSIBILITY.md

Blind_Log is designed for visually impaired users and must remain accessible.

Requirements:

* Keyboard-first interface is mandatory.
* All primary actions must be reachable by keyboard shortcuts and menu accelerators.
* Focus order must be predictable and preserved in dialogs and the main window.
* NVDA output is used for notifications and field state announcements.
* Do not rely on mouse-only controls or hidden actions.
* Dialogs must be navigable with Tab and have clear labels.
* Use `wx.CallAfter` for UI updates from background operations.
* Do not break screen reader compatibility or focus restoration.
* If a field is hidden, notify the user instead of failing silently.
* Maintain visible field selection without breaking journal column layout.
