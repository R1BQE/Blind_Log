# TODO_AI.md

- Review `gui.py` for UI/business logic separation and move data handling to controller if needed.
- Consider reducing broad `except Exception` blocks in UI and manager modules.
- Improve update flow separation: network check in `updater.py` vs dialog rendering.
- Add tests for QRZ lookup and `SettingsDialog` behavior.
- Verify help file language selection logic is consistent across settings and main UI.
- Confirm `auto_temp` restore behavior in edge cases with corrupted temp data.
