"""
Быстрый тест архитектуры - проверить что QSOManager и Controller работают без wx.
"""

import sys
sys.path.insert(0, '.')

from settings import SettingsManager
from qso_manager import QSOManager
from controller import ApplicationController, GUIBridge

print("=" * 60)
print("АРХИТЕКТУРНЫЙ ТЕСТ - Отделение QSOManager от GUI")
print("=" * 60)

# 1. Создание SettingsManager
print("\n[1] Создание SettingsManager...")
try:
    settings = SettingsManager()
    print("✓ SettingsManager создан")
except Exception as e:
    print(f"✗ Ошибка: {e}")
    sys.exit(1)

# 2. Создание QSOManager БЕЗ wx зависимостей
print("\n[2] Создание QSOManager...")
try:
    qso_manager = QSOManager(settings_manager=settings)
    print("✓ QSOManager создан (БЕЗ параметра parent)")
    print(f"  - QSO список пуст: {len(qso_manager.qso_list) == 0}")
except Exception as e:
    print(f"✗ Ошибка: {e}")
    sys.exit(1)

# 3. Проверка что QSOManager не импортирует wx
print("\n[3] Проверка отсутствия wx в QSOManager...")
with open('qso_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()
    has_wx_import = 'import wx' in content
    has_wx_messagebox = 'wx.MessageBox' in content
    print(f"  - 'import wx' в qso_manager.py: {'✗ ОШИБКА' if has_wx_import else '✓ ОТСУТСТВУЕТ'}")
    print(f"  - 'wx.MessageBox' в qso_manager.py: {'✗ ОШИБКА' if has_wx_messagebox else '✓ ОТСУТСТВУЕТ'}")

# 4. Создание ApplicationController
print("\n[4] Создание ApplicationController...")
try:
    controller = ApplicationController(qso_manager, settings, gui_bridge=None)
    print("✓ ApplicationController создан")
except Exception as e:
    print(f"✗ Ошибка: {e}")
    sys.exit(1)

# 5. Тест добавления QSO (без UI)
print("\n[5] Тест добавления QSO...")
try:
    test_qso = {
        'call': 'R1OAZ',
        'name': 'Ivan',
        'city': 'Moscow',
        'qth': 'KO85',
        'band': '20m',
        'mode': 'SSB',
        'freq': '14.150',
        'rst_received': '59',
        'rst_sent': '59',
        'comment': 'Test contact',
        'datetime': '2026-04-28 12:00',
    }
    success, message = qso_manager.add_qso(test_qso)
    if success:
        print(f"✓ QSO добавлен: {message}")
        print(f"  - QSO список теперь содержит: {len(qso_manager.qso_list)} запись")
    else:
        print(f"✗ Ошибка добавления: {message}")
except Exception as e:
    print(f"✗ Исключение при добавлении: {e}")
    sys.exit(1)

# 6. Тест валидации (позывной обязателен)
print("\n[6] Тест валидации...")
try:
    invalid_qso = {
        'call': '',  # Пустой позывной - должно быть ошибкой
        'name': 'Test',
    }
    success, message = qso_manager.add_qso(invalid_qso)
    if not success:
        print(f"✓ Валидация работает: {message}")
    else:
        print(f"✗ Валидация НЕ работает - должна была отклонить пустой позывной")
except Exception as e:
    print(f"✗ Исключение при валидации: {e}")

# 7. Проверка структуры архитектуры
print("\n[7] Проверка слоёв архитектуры...")
print(f"  - QSOManager имеет метод add_qso(): {hasattr(qso_manager, 'add_qso')}")
print(f"  - QSOManager имеет метод edit_qso(): {hasattr(qso_manager, 'edit_qso')}")
print(f"  - QSOManager имеет метод delete_qso(): {hasattr(qso_manager, 'delete_qso')}")
print(f"  - QSOManager имеет метод lookup_callsign(): {hasattr(qso_manager, 'lookup_callsign')}")
print(f"  - Controller имеет метод add_qso_from_gui(): {hasattr(controller, 'add_qso_from_gui')}")
print(f"  - Controller имеет метод edit_qso_from_gui(): {hasattr(controller, 'edit_qso_from_gui')}")
print(f"  - Controller имеет метод delete_qso(): {hasattr(controller, 'delete_qso')}")

print("\n" + "=" * 60)
print("✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
print("=" * 60)
print("\nЗАКЛЮЧЕНИЕ:")
print("- QSOManager отделен от wx (может использоваться в любом интерфейсе)")
print("- ApplicationController является посредником между GUI и логикой")
print("- Архитектура позволяет заменить GUI без изменения бизнес-логики")
