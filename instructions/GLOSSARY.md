# GLOSSARY.md

QSO — radio contact record in the log.

ADIF — Amateur Data Interchange Format, standard format for log export/import.

QRZ — callsign database service used for automatic lookup.

NVDA — screen reader used for accessibility.

Band — amateur radio band (e.g. 40m, 20m).

Mode — operating mode (e.g. SSB, CW, FM, AM).

Callsign — radio station identifier.

Grid Locator / QTH — station location reference. In Blind_Log the `qth` field stores grid locator data, while `city` stores the station city/QTH.

LoTW — Logbook of The World, a service for which transliterated callsign data is useful when exporting logs.

Club Log — online amateur logbook service often used with ADIF exports.

eQSL — electronic QSL service often compatible with transliterated station data.

GUIBridge — interface between controller and UI.

QSOManager — business logic manager for QSO data.

ApplicationController — coordinator between GUI and QSOManager.

SettingsManager — settings loader and saver.

Exporter — module exporting QSO data to ADIF.

Importer — module importing ADIF into internal QSO format.

Updater — module checking GitHub releases for updates.

Translation / `tr(...)` — function for localized text.
