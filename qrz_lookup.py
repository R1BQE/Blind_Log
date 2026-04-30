import requests
import logging
import xml.etree.ElementTree as ET
from utils import Result

class QRZLookup:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session_key = None
        self.agent = "blind_log"
        self.base_url = "https://api.qrz.ru/"

    def login(self):
        try:
            url = f"{self.base_url}login"
            params = {
                "u": self.username,
                "p": self.password,
                "agent": self.agent
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.text
            root = ET.fromstring(data)
            # QRZ.ru возвращает <Session> (с большой буквы), а не <session_id> напрямую
            # root -> QRZDatabase -> Session -> session_id
            session_id = None
            for session_elem in root.iter():
                if session_elem.tag.lower().endswith('session'):
                    for child in session_elem:
                        if child.tag.lower().endswith('session_id') and child.text:
                            session_id = child.text.strip()
                            break
            if session_id:
                self.session_key = session_id
                logging.info(f"Успешная авторизация на QRZ.ru, session_id: {self.session_key}")
                print(f"Успешная авторизация на QRZ.ru, session_id: {self.session_key}")
                return Result(True, data=session_id)
            else:
                # Пробуем найти ошибку
                error = root.find('.//error')
                if error is not None:
                    logging.error(f"Ошибка авторизации на QRZ.ru: {error.text}")
                    print(f"Ошибка авторизации на QRZ.ru: {error.text}")
                    return Result(False, error=error.text.strip() if error.text else "Ошибка авторизации на QRZ.ru")
                else:
                    logging.error(f"Ошибка авторизации на QRZ.ru: {data}")
                    print(f"Ошибка авторизации на QRZ.ru: {data}")
                    return Result(False, error=data)
        except Exception as e:
            logging.error(f"Ошибка авторизации: {e}")
            print(f"Ошибка авторизации: {e}")
            return Result(False, error=str(e))

    def lookup_call(self, callsign):
        if not self.session_key:
            logging.error("Нет session key. Выполните авторизацию.")
            print("Нет session key. Выполните авторизацию.")
            return Result(False, error="Нет session key. Выполните авторизацию.")
        try:
            url = f"{self.base_url}callsign"
            params = {
                "id": self.session_key,
                "callsign": callsign
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.text
            root = ET.fromstring(data)
            # Ищем первый тег Callsign (без учёта namespace)
            callsign_elem = None
            for elem in root.iter():
                if elem.tag.lower().endswith('callsign'):
                    callsign_elem = elem
                    break
            if callsign_elem is not None:
                def get_text(tag):
                    # Ищем только точное совпадение тега (без вхождения в другие, например, surname)
                    for child in callsign_elem:
                        if child.tag.lower().split('}')[-1] == tag and child.text:
                            return child.text.strip()
                    return ""
                result = {
                    "name": get_text("name"),
                    "city": get_text("city"),
                }
                logging.info(f"QRZ result for {callsign}: {result}")
                print(f"QRZ result for {callsign}: {result}")
                return Result(True, data=result)
            else:
                # Пробуем найти ошибку
                error = None
                for elem in root.iter():
                    if elem.tag.lower().endswith('error') and elem.text:
                        error = elem.text.strip()
                        break
                if error is not None:
                    logging.info(f"Позывной {callsign} не найден в базе QRZ.ru: {error}")
                    print(f"Позывной {callsign} не найден в базе QRZ.ru: {error}")
                    return Result(False, error=error)
                else:
                    logging.info(f"Позывной {callsign} не найден в базе QRZ.ru: {data}")
                    print(f"Позывной {callsign} не найден в базе QRZ.ru: {data}")
                    return Result(False, error=data)
        except Exception as e:
            logging.error(f"Ошибка поиска позывного: {e}")
            print(f"Ошибка поиска позывного: {e}")
            return Result(False, error=str(e))