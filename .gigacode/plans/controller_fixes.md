# План исправлений controller.py

## Критические проблемы

### 1. Синтаксическая ошибка (строка 432)
**Проблема:** Вложенная двойная кавычка в f-string вызывает `SyntaxError`.
```python
# Было (неправильно):
error_msg = f"{_("settings_load_error")}: {str(e)}"

# Стало (правильно):
error_msg = f"{_('settings_load_error')}: {str(e)}"
```

### 2. Дублирующий импорт `logger` (строка 10)
**Проблема:** Дублирование импорта `logger` нарушает чистоту архитектуры.
```python
# Удалить строку:
import logger

# Оставить импорты:
from logger import log_user_action, log_ui_state, log_feedback, log_error
```

### 3. Замена `logger.exception` на `log_error` (строка 434)
**Проблема:** После удаления `import logger` вызов `logger.exception(...)` перестанет работать.
```python
# Было:
logger.exception("Settings load error")

# Стало:
log_error(f"{_('settings_load_error')}: {str(e)}")
```

## Дополнительные действия

1. Проверить `qso_manager.py` на отсутствие прямых вызовов `wx.MessageBox`.
2. Запустить тесты: `pytest tests/`.
3. Убедиться, что `QSOManager.load_temp()` возвращает `Result`, а не вызывает UI.
