# PROJECT_MAP.md

## Root files

* `main.py` — application entry point, инициализация `wx.App`, загрузка настроек и запуск главного окна.
* `readme.md` — текущая документация проекта.
* `ARCHITECTURE.md` — описание архитектуры.
* `readme_ru.md` — русскоязычная версия readme.
* `requirements.txt` — список Python зависимостей.
* `version.txt` — информация о версии и продукте для сборки.
* `changelog-ru.txt`, `changelog-en.txt` — тексты истории изменений (русский и английский).
* `constants.py` — константы приложения, используемые в UI (`gui/`) и других модулях.
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

* `gui/` — пакет главного wxPython окна и его mixin-модулей.
  * `Blind_log` — главное окно с двумя вкладками: добавление QSO и журнал.
  * `GUIBridgeImpl` — реализация интерфейса `GUIBridge` для контроллера.

* `controller.py` — `ApplicationController` и абстракция `GUIBridge`.
  * принимает команды от UI;
  * координирует бизнес-логику и уведомления.
* `controller_qso_actions.py` — чтение формы и операции с записями QSO.
* `controller_import.py` — импорт ADIF и обновление журнала после импорта.
* `controller_draft.py` — правила сохранения, загрузки и очистки черновика.
* `controller_export.py` — экспорт журнала в ADIF через контроллер.

* `qso_manager.py` — загрузка журнала, черновики, дата/время и настройки менеджера.
* `qso_operations.py` — нормализация, валидация, добавление, редактирование, удаление и импорт записей QSO.

* `settings.py` — менеджер настроек, загружает/сохраняет `settings.ini`.
* `settings_dialog.py` — UI диалога настроек.

* `exporter.py` — экспорт в ADIF.
  * формирует ADIF-запись из текущих QSO.
  * использует `adif-io`.

* `importer.py` — импорт ADIF.
  * парсит файлы ADIF и возвращает внутренние QSO словари.
  * поддерживает cp1251 и utf-8.

* `update_service.py` — проверка обновлений через GitHub Releases API без UI.
* `updater.py` — диалоги и orchestration обновления.
* `update_installer.py` — скачивание, распаковка и установка обновлений.
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

* `scripts/extract_changelog.py` — извлекает последнюю запись из `changelog-en.txt` для описания релиза, добавляет ссылку на русскую версию.

## CI/CD

* `.github/workflows/release.yml` — сборка и публикация релиза в GitHub Releases (windows-latest runner).

## Resource files

* `help.htm`, `help_en.htm` — встроенная справка.
* `locales/en.json`, `locales/ru.json` — переводы интерфейса.
* `changelog-ru.txt`, `changelog-en.txt` — истории изменений на русском и английском.

## Test files

* `tests/conftest.py` — фикстуры для тестов.
* `tests/test_qso_manager.py` — тесты `QSOManager` и постоянного хранения журнала.
* `tests/test_controller.py` — тесты команд контроллера для добавления, удаления и редактирования QSO.
* `tests/test_controller_import.py` — тесты ADIF-импорта через контроллер.
* `tests/test_controller_draft.py` — тесты жизненного цикла черновика через контроллер.
* `tests/test_controller_export.py` — тесты экспорта ADIF через контроллер.
* `tests/test_exporter.py` — тесты экспорта ADIF.
* `tests/test_updater.py` — тесты проверки обновлений.
* `tests/test_i18n.py` — тесты локализации.

## Связи между компонентами

* `main.py` -> `SettingsManager`, `QSOManager`, `Blind_log`, `check_update`
* `Blind_log` -> `ApplicationController`, `GUIBridgeImpl`; окно больше не создаёт `Exporter` напрямую.
* `ApplicationController` -> `QSOManager`, `GUIBridge`, импортёр ADIF и `Exporter`; UI использует контроллер для черновиков и экспорта.
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
