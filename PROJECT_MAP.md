# PROJECT_MAP.md

## Root files

* `main.py` — application entry point, инициализация `wx.App`, загрузка настроек и запуск главного окна.
* `readme.md` — текущая документация проекта.
* `ARCHITECTURE.md` — описание архитектуры.
* `readme_ru.md` — русскоязычная версия readme.
* `requirements.txt` — список Python зависимостей.
* `version.txt` — информация о версии и продукте для сборки.
* `changeLog.txt` — текст истории изменений.
* `constants.py` — константы приложения, используемые в UI (`gui.py`) и других модулях.
* `transliterator.py` — транслитерация данных корреспондента (используется для совместимости с LoTW/Club Log/eQSL).
* `update_version.py` — скрипт обновления номера версии перед сборкой/релизом.
* `settings.ini` — пользовательские настройки приложения. **Генерируется во время выполнения, в git не хранится.**
* `blind_log_temp.json` — временный файл автосохранения сессии. **Генерируется во время выполнения, в git не хранится.**
* `help.htm` — локальная справка на русском.
* `help_en.htm` — локальная справка на английском.
* `settings_storage.py` — абстракция файла настроек.
* `welcome_dialog.py` — диалог первого запуска.
* `compile.bat` — сборка приложения через PyInstaller.
* `Blind_log.spec` — спецификация PyInstaller для основного приложения.
* `updater.spec` — спецификация PyInstaller для отдельного апдейтер-исполняемого файла.
* `.gitattributes`, `.gitignore` — служебные файлы git.

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
  * обрабатывает редактирование, удаление, автосохранение.
  * вызывает `transliterator.py` для транслитерации данных корреспондента.
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

* `transliterator.py` — транслитерация.
  * преобразует данные корреспондента для совместимости с LoTW/Club Log/eQSL.

* `utils.py` — утилиты.
  * `Result` класс, путь к ресурсам, версия.

* `logger.py` — структурированное логирование.
  * функции `log_user_action`, `log_ui_state`, `log_feedback`, `log_error`, `log_debug`.

* `welcome_dialog.py` — диалог первого запуска.
  * показывает текст на английском и русском.
  * предлагает открыть настройки.

## Scripts

* `scripts/commit_changelog.py` — коммитит переведённый changelog обратно в репозиторий. Известная проблема: падение на кириллице в Windows CI (см. CODE_REVIEW.md).
* `scripts/extract_changelog.py` — извлекает секцию changelog для текущей версии.
* `scripts/translate_changelog.py` — переводит changelog на другие языки.
* `scripts/install_argos_package.py` — устанавливает языковой пакет Argos Translate для офлайн-перевода.

## CI/CD

* `.github/workflows/release.yml` — сборка и публикация релиза в GitHub Releases (windows-latest runner).

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
* `QSOManager` -> `SettingsManager`, `QRZLookup`, `transliterator`
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
* Transliteration (`transliterator.py`)
* Changelog automation (`scripts/`)
* Release build (`.github/workflows/release.yml`, `Blind_log.spec`, `updater.spec`)
