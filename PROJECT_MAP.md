# PROJECT_MAP.md

## Root files

* `main.py` — application entry point, инициализация `wx.App`, загрузка настроек и запуск главного окна.
* `README.md` — текущая документация проекта.
* `ARCHITECTURE.md` — описание архитектуры.
* `README_ru.md` — русскоязычная версия README.
* `requirements.txt` — список Python зависимостей.
* `version.txt` — информация о версии и продукте для сборки.
* `changeLog.txt` — текст истории изменений.
* `settings.ini` — пользовательские настройки приложения.
* `blind_log_temp.json` — временный файл автосохранения сессии.
* `help.htm` — локальная справка на русском.
* `help_en.htm` — локальная справка на английском.
* `settings_storage.py` — абстракция файла настроек.
* `welcome_dialog.py` — диалог первого запуска.
* `compile.bat` — сборка приложения через PyInstaller.
* `Blind_log.spec` — спецификация PyInstaller.

## Main application modules

* `gui.py` — главный wxPython интерфейс и UI Bridge.
  * `Blind_log` — главное окно с двумя вкладками: добавление QSO и журнал.
  * `GUIBridgeImpl` — реализация интерфейса `GUIBridge` для контроллера.

* `controller.py` — `ApplicationController` и абстракция `GUIBridge`.
  * принимает команды от UI.
  * читает данные из контролов.
  * вызывает `QSOManager` и `Exporter`.
  * обрабатывает исключения и уведомляет пользователя.

* `qso_manager.py` — бизнес-логика QSO.
  * `QSOManager` хранит список QSO и управляет валидностью.
  * обрабатывает редактирование, удаление, автосохранение и транслитерацию.
  * интегрируется с `QRZLookup`.

* `settings.py` — менеджер настроек и диалог настроек.
  * `SettingsManager` загружает/сохраняет `settings.ini`.
  * `SettingsDialog` строит UI настроек.

* `exporter.py` — экспорт в ADIF.
  * формирует ADIF-запись из текущих QSO.
  * использует `adif-io`.

* `importer.py` — импорт ADIF.
  * парсит файлы ADIF и возвращает внутренние QSO словари.
  * поддерживает cp1251 и utf-8.

* `updater.py` — проверка обновлений.
  * обращается к GitHub Releases API.
  * показывает диалоги загрузки и обновления.

* `qrz_lookup.py` — QRZ.ru API.
  * логин и поиск позывного.

* `nvda_notify.py` — уведомления через `accessible-output3`.
  * fallback-поведение через `wx.adv.NotificationMessage`.

* `i18n.py` — локализация.
  * загрузка переводов из JSON файлов.
  * определение доступных языков.

* `settings_storage.py` — чтение/запись конфигурации.
  * абстракция работы с файлом `settings.ini`.

* `utils.py` — утилиты.
  * `Result` класс, путь к ресурсам, версия.

* `logger.py` — структурированное логирование.
  * функции `log_user_action`, `log_ui_state`, `log_feedback`, `log_error`, `log_debug`.

* `welcome_dialog.py` — диалог первого запуска.
  * показывает текст на английском и русском.
  * предлагает открыть настройки.

## Resource files

* `help.htm`, `help_en.htm` — встроенная справка.
* `locales/en.json`, `locales/ru.json` — переводы интерфейса.
* `changeLog.txt` — changelog с размеченными языковыми секциями.

## Test files

* `tests/conftest.py` — фикстуры для тестов.
* `tests/test_qso_manager.py` — тесты `QSOManager`.
* `tests/test_exporter.py` — тесты экспорта ADIF.
* `tests/test_updater.py` — тесты проверки обновлений.
* `tests/test_i18n.py` — тесты локализации.

## Связи между компонентами

* `main.py` -> `SettingsManager`, `QSOManager`, `Blind_log`, `check_update`
* `Blind_log` -> `ApplicationController`, `Exporter`, `GUIBridgeImpl`
* `ApplicationController` -> `QSOManager`, `Exporter`, `importer`, `GUIBridge`
* `QSOManager` -> `SettingsManager`, `QRZLookup`
* `Exporter` -> `QSOManager`, `SettingsManager`
* `importer.py` -> `adif-io`
* `updater.py` -> GitHub API, `wx` для диалогов
* `nvda_notify.py` -> `accessible-output3` / wx fallback

## Точки входа

* `main.py` — основной запуск приложения.
* `compile.bat` — сборка исполняемого файла.

## Основные сервисы

* QSO management (`qso_manager.py`)
* ADIF export/import (`exporter.py`, `importer.py`)
* QRZ lookup (`qrz_lookup.py`)
* Update checker (`updater.py`)
* Settings manager (`settings.py`, `settings_storage.py`)
* Localization (`i18n.py`, `locales/`)
* NVDA notifications (`nvda_notify.py`)