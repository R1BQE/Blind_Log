# Blind_log

[Русская версия](readme_ru.md)

**Blind_log** is an amateur radio logbook application designed specifically for visually impaired operators. The program allows you to conveniently add, edit, delete, and export QSO records, and includes features that simplify on-air operations.

## Features

- **Add, edit, and delete QSO records**  
  Accessible and convenient interface for working with contacts.

- **Export to ADIF format**  
  The log can be exported to the universal ADIF format for use in other logging tools and services. The export button is removed from the main interface — use **Ctrl+S** on the "Journal" tab.

- **Safe shutdown handling**  
  If there is at least one record in the journal, the program prompts to save the log in ADIF format, exit without saving, or cancel exiting.

- **Flexible settings**  
  You can set operator callsign, name, QTH, equipment, timezone, and other parameters through the settings dialog.

- **Date and time handling**  
  Current date and time are set automatically with timezone support. Manual adjustment is also available.

- **Update check**  
  The program can check for a new version manually (via the "Help" menu or **Ctrl+U**) or automatically at startup if enabled in settings.

- **Keyboard shortcuts**  
  Extended shortcut support for faster operation (see below).

- **NVDA notification support**  
  Important events are spoken through the NVDA screen reader when `nvdaControllerClient64.dll` is available.

---

## Installation

1. Download the latest version zip archive:  
   [Download latest release](https://github.com/r1oaz/Blind_Log/releases/latest/download/Blind_log.zip)  
2. Extract the archive to a folder of your choice.

## Usage

1. Run the application. Administrator privileges are not required.
2. Use the "Add QSO" and "Journal" tabs to work with contacts.
3. Configure settings via the "Settings" menu.

---

## Keyboard Shortcuts

- **Ctrl+P** — Open settings
- **Ctrl+Q** — Exit the application
- **Ctrl+Enter** — Add QSO
- **Ctrl+E** — Edit selected QSO
- **Ctrl+S** — Export QSO to ADIF (shortcut only)
- **Delete** — Delete selected QSO
- **Shift+F1** — About
- **F1** — Help
- **Ctrl+Tab** — Switch tabs forward
- **Ctrl+Shift+Tab** — Switch tabs backward
- **Ctrl+U** — Check for updates
- **Enter** — Fill name and city from QRZ.ru by callsign (if enabled)

---

## Contacts

Send feedback and suggestions to:  
📧 [administrator@r1oaz.ru](mailto:administrator@r1oaz.ru)
