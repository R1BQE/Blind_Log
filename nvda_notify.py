# nvda_notify.py
"""
Модуль для озвучивания сообщений через NVDA с помощью controllerClient.dll.
"""
import sys
import ctypes
import os
import wx
from logger import log_feedback, log_error

class NVDAController:
    def __init__(self):
        self.dll = None
        self.available = False
        try:
            # Определяем путь к DLL: сначала ищем рядом с exe, затем внутри PyInstaller bundle
            if getattr(sys, 'frozen', False):
                # PyInstaller: DLL будет распакована во временную папку _MEIPASS
                base_path = sys._MEIPASS
            else:
                base_path = os.getcwd()
            dll_path = os.path.join(base_path, 'nvdaControllerClient64.dll')
            if os.path.exists(dll_path):
                self.dll = ctypes.WinDLL(dll_path)
                # Используем правильную функцию NVDA
                self.dll.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
                self.dll.nvdaController_speakText.restype = ctypes.c_int
                self.available = True
        except Exception as e:
            log_error(f"NVDA DLL loading error: {e}")
            self.available = False

    def speak(self, message: str, interrupt: bool = True):
        log_feedback(message)
        if self.available and self.dll:
            try:
                res = self.dll.nvdaController_speakText(message)
                if res != 0:
                    log_error(f"NVDA speakText error: code {res}")
            except Exception as e:
                log_error(f"nvdaController_speakText call error: {e}")
        else:
            wx.adv.NotificationMessage("Blind_Log", message).Show()
            log_error("NVDA DLL unavailable, fallback to wx.adv.NotificationMessage")

# Глобальный экземпляр для использования в других модулях
nvda_controller = NVDAController()

def nvda_notify(message: str, interrupt: bool = True):
    """
    Озвучить сообщение через NVDA, если controllerClient.dll доступен.
    """
    nvda_controller.speak(message, interrupt)
    # Для отладки также выводим в консоль
    print(f"NVDA_NOTIFY: {message}")
    log_feedback(f"NVDA_NOTIFY: {message}")
