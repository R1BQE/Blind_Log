# ARCHITECTURE.md

Этот файл описывает архитектуру текущего состояния проекта Blind_Log.

# Общая информация

Blind_Log — это настольное приложение для ведения журнала радиосвязей (QSO) радиолюбителя.
Приложение нацелено на работу с клавиатурой и совместимость с экранным диктором NVDA.

Проект написан на Python и wxPython.

# Точка входа

* `main.py`

# Основные компоненты

* `gui.py` — wxPython интерфейс, главное окно, меню, диалоги, ускорители клавиш, фокус и NVDA-уведомления.
* `controller.py` — `ApplicationController` и `GUIBridge`, посредник между GUI и бизнес-логикой.
* `qso_manager.py` — менеджер QSO: добавление, редактирование, удаление, валидация, нормализация, автосохранение, QRZ.ru.
* `settings.py` — `SettingsManager` и `SettingsDialog`, управление настройками и видимостью полей.
* `exporter.py` — экспорт журнала в ADIF.
* `importer.py` — импорт ADIF через `adif-io`.
* `updater.py` — проверка обновлений на GitHub Releases и показ диалогов.
* `qrz_lookup.py` — интеграция с QRZ.ru XML API.
* `nvda_notify.py` — уведомления через `accessible-output3` и fallback через wx.
* `i18n.py` — загрузка переводов из `locales/*.json`.
* `settings_storage.py` — чтение и запись `settings.ini`.
* `welcome_dialog.py` — первый запуск и диалог приветствия.
* `utils.py` — утилиты, `Result`, пути и версия.

# Архитектурные слои

## UI Layer

Файлы: `gui.py`, `welcome_dialog.py`, часть `settings.py`.

Обеспечивает:

* главное окно с двумя вкладками: добавление QSO и журнал
* меню и контекстное меню
* диалоги настроек, «О программе», «Что нового», импорт/экспорт
* горячие клавиши и accelerators
* работу с фокусом и NVDA-сообщения
* открытие внутренних HTML-файлов помощи

UI не должен содержать бизнес-логику QSO и не должен напрямую изменять данные без контроллера.

## Controller Layer

Файл: `controller.py`.

Обеспечивает:

* выполнение действий пользователя из GUI
* чтение данных из GUI через `GUIBridge`
* вызовы `QSOManager` и `Exporter`
* обновление GUI через `GUIBridge`
* обработку ошибок и уведомления
* выполнение фоновых операций в UI-потоке

`ApplicationController` не должен выполнять низкоуровневый GUI-код, он использует абстракцию `GUIBridge`.

## Business Logic Layer

Файл: `qso_manager.py`.

Отвечает за:

* хранение списка `qso_list`
* добавление, редактирование, удаление записей
* валидацию полей QSO
* нормализацию входных данных
* автосохранение временной сессии (`blind_log_temp.json`)
* QRZ.ru lookup wrapper
* управление режимом редактирования

`QSOManager` не зависит от wxPython и не должен отображать диалоги или обновлять UI.

## Infrastructure Layer

Файлы: `settings.py`, `settings_storage.py`, `exporter.py`, `importer.py`, `updater.py`, `qrz_lookup.py`, `nvda_notify.py`, `i18n.py`, `utils.py`, `logger.py`.

Обеспечивает:

* параметры и хранение конфигурации
* сериализацию/десериализацию ADIF
* работу с QRZ.ru
* проверку доступности модулей и обновления
* локализацию и сообщения
* логирование и уведомления

# Поток запуска

1. `main.py` создает `MyApp`.
2. `SettingsManager` загружает `settings.ini` или создает его с дефолтными значениями.
3. Инициализируется логирование по настройке `log_enabled`.
4. Загружаются переводы через `i18n.load_translations()`.
5. При первом запуске показывается `welcome_dialog.show_welcome_dialog()`.
6. При необходимости открывается диалог настроек.
7. Запускается проверка обновлений (`updater.check_update`) если включена.
8. Создается `QSOManager(settings_manager=...)`.
9. Создается `Blind_log` окно с `GUIBridgeImpl` и `ApplicationController`.
10. Если включен `auto_temp`, загружается temp-сессия и предлагается восстановление.
11. Запускается основной цикл wxPython `app.MainLoop()`.

# Взаимодействие модулей

* `gui.py` использует `ApplicationController` для команд пользователя.
* `ApplicationController` вызывает `QSOManager` и `Exporter`, импортирует `importer` для ADIF и инициирует QRZ lookup через `QSOManager`.
* `QSOManager` использует `SettingsManager` для конфигурации и `QRZLookup` для lookup.
* `Exporter` использует `SettingsManager` для заголовков ADIF и список QSO из `QSOManager`.
* `importer.py` парсит ADIF и возвращает внутренние QSO словари.
* `i18n.py` загружает JSON-переводы, которые применяются в UI и логике.
* `nvda_notify.py` обеспечивает речевые уведомления через `accessible-output3` и fallback.

# Данные и форматы

* QSO хранится как словарь с полями: `call`, `name`, `city`, `qth`, `band`, `mode`, `freq`, `rst_received`, `rst_sent`, `comment`, `datetime`.
* Внутренний `datetime` хранится как строка `YYYY-MM-DD HH:MM[:SS]`.
* Экспорт ADIF использует `ADIF_VER 3.1.7`.
* Импорт ADIF поддерживает cp1251 и utf-8.

# Ограничения архитектуры

* `gui.py` должен оставаться UI-слоем и не содержать бизнес-логику.
* `qso_manager.py` не должен использовать wxPython или диалоги.
* Локализация всегда проходит через `tr(...)`.
* Настройки должны хранить коды, а не переводы.
* Фоновые операции не должны напрямую обновлять UI без `wx.CallAfter`.
* Любые диалоговые сообщения из бизнес-логики должны идти через контроллер или GUI.

---

### updater.py

Назначение:

* проверка обновлений
* работа с GitHub Releases
* загрузка обновлений
* распаковка архива
* подготовка PowerShell update script

Обновление выполняется в фоне.

---

### qrz_lookup.py

Назначение:

* работа с QRZ.ru API
* login
* callsign lookup

Используется для автоматического получения данных корреспондента.

---

### i18n.py

Назначение:

* загрузка переводов
* переключение языка
* функция tr(...)
* fallback localization

Все строки интерфейса должны проходить через:

* tr(...)

Запрещено:

* хардкодить UI строки
* использовать локализованный текст в логике

---

### logger.py

Назначение:

* централизованное логирование
* traceback
* debug logging
* error logging

---

# Карта модулей

## main.py

Точка входа приложения.

Зависимости:

* gui
* settings
* updater
* i18n
* logger

---

## gui.py

UI приложения.

Зависимости:

* controller
* qso_manager
* exporter
* settings
* constants
* i18n
* nvda_notify

Отслеживание ручного редактирования даты/времени:

* _datetime_manual_override: флаг, указывающий на ручное изменение даты/времени
* _suppress_datetime_change_events: флаг для подавления событий при программной установке
* on_datetime_control_change(): обработчик события изменения даты/времени
* _reset_datetime_override(): сброс флага при добавлении новой записи
* _set_datetime_change_suppression(): управление подавлением событий

Логика:

* При добавлении новой QSO автоматически заполняется текущее время
* Если пользователь вручную изменяет дату или время, флаг активируется
* Таймер автообновления проверяет флаг и не перезаписывает изменённые значения
* При переключении на вкладку добавления сброс флага позволяет заново автозаполнять поля

---

## controller.py

Controller layer.

Зависимости:

* qso_manager
* GUIBridge
* logger

---

## qso_manager.py

Business logic.

Зависимости:

* utils
* qrz_lookup
* datetime
* storage/temp

---

## exporter.py

ADIF export subsystem.

---

## importer.py

ADIF import subsystem.

Зависимости:

* adif_io

Обработка:

* читает ADIF-файл через `adif_io.read_from_file()`
* преобразует каждую запись в внутренний словарь QSO
* возвращает список QSO для импорта
* поддерживает cp1251 и utf-8

---

## settings.py

Settings subsystem.

---

## updater.py

Update subsystem.

---

## qrz_lookup.py

QRZ API subsystem.

---

## i18n.py

Localization subsystem.

---

# Поток данных

## Добавление QSO

1. Пользователь вводит данные в форму
2. GUI вызывает controller.add_qso_from_gui()
3. Controller получает значения через GUIBridge
4. Формируется словарь/объект QSO
5. QSOManager выполняет:

   * validation
   * normalization
   * conversion
6. QSO сохраняется
7. Controller обновляет GUI
8. Пользователь получает уведомление

---

## Экспорт

1. Пользователь запускает экспорт
2. Exporter получает:

   * qso_list
   * settings
3. Формируется ADIF
4. Файл сохраняется на диск

---

## Импорт

1. Пользователь выбирает ADIF-файл
2. Importer читает файл
3. Выполняется парсинг записей
4. Данные преобразуются во внутренний формат
5. QSOManager выполняет валидацию
6. Записи добавляются в журнал
7. GUI обновляет отображение журнала

---

# Потоки и асинхронность

Фоновые задачи:

* QRZ lookup
* update checking

выполняются через thread.

Worker thread не должен напрямую изменять GUI.

Для возврата в UI thread используется:

* wx.CallAfter

---

# Доступность

Проект ориентирован на незрячих пользователей.

Критически важно сохранять:

* keyboard navigation
* tab order
* NVDA compatibility
* focus restoration
* spoken notifications
* predictable interaction flow

Нельзя:

* вводить mouse-only функциональность
* ломать keyboard workflow
* удалять уведомления без альтернативы

---

# Локализация

Локализация основана на:

* i18n.py
* locales/*.json

Базовый язык:

* English

Поддерживается:

* auto language selection
* ручной выбор языка

Все UI строки должны использовать:

* tr(...)

---

# Временные данные

Приложение поддерживает:

* temp save
* session restore

Цель:

* минимизация потери данных при сбое

---

# Тестирование

Основное покрытие:

* qso_manager
* exporter
* importer

Недостаточное покрытие:

* controller
* GUI bridge
* threading scenarios

Рекомендуется:

* unit tests
* integration tests
* regression tests

---

# Известные проблемы и технический долг

## Текущие риски

1. Возможные runtime ошибки в controller.py
2. Смешение UI и логики в отдельных местах
3. Хрупкая логика timezone settings
4. Несогласованный Result contract
5. Legacy code в репозитории
6. Слишком широкие except

---

## Технический долг

Проблемные зоны:

* UI calls внутри logic layer
* отсутствие централизованной схемы полей
* недостаточное покрытие тестами
* неполная детализация логирования

---

# Правила развития проекта

При внесении изменений важно:

* сохранять разделение слоёв
* не смешивать GUI и бизнес-логику
* не ломать доступность
* минимизировать diff
* избегать ненужных рефакторингов
* сохранять обратную совместимость

---

# Основной принцип проекта

Стабильность и доступность важнее:

* визуальных изменений
* архитектурных экспериментов
* крупных рефакторингов
* модных паттернов
* переписывания работающего кода
