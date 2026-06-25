import requests
import xml.etree.ElementTree as ET
from utils import Result
from logger import log_user_action, log_error

class QRZLookup:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session_key = None
        self.agent = "blind_log"
        self.base_url = "https://api.qrz.ru/"

    def login(self):
        log_user_action("Start QRZ authorization")
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
                log_user_action("Successful QRZ.ru authorization")
                return Result(True, data=session_id)
            else:
                # Пробуем найти ошибку
                error = root.find('.//error')
                if error is not None:
                    log_error(f"QRZ.ru authorization error: {error.text}")
                    return Result(False, error=error.text.strip() if error.text else "QRZ.ru authorization error")
                else:
                    log_error(f"QRZ.ru authorization error: {data}")
                    return Result(False, error=data)
        except requests.RequestException as e:
            log_error(f"QRZ network error during login: {e}")
            return Result(False, error=str(e))
        except ET.ParseError as e:
            log_error(f"QRZ XML parse error during login: {e}")
            return Result(False, error=f"XML parse error: {e}")

    def lookup_call(self, callsign):
        log_user_action(f"Start searching for callsign {callsign}")
        if not self.session_key:
            log_error("No session key. Please authorize first.")
            return Result(False, error="No session key. Please authorize first.")
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
                log_user_action(f"QRZ: data found for {callsign}")
                return Result(True, data=result)
            else:
                # Пробуем найти ошибку
                error = None
                for elem in root.iter():
                    if elem.tag.lower().endswith('error') and elem.text:
                        error = elem.text.strip()
                        break
                if error is not None:
                    log_user_action(f"Callsign {callsign} not found in QRZ.ru database")
                    return Result(False, error=error)
                else:
                    log_user_action(f"Callsign {callsign} not found in QRZ.ru database")
                    return Result(False, error=data)
        except requests.RequestException as e:
            log_error(f"QRZ network error during lookup: {e}")
            return Result(False, error=str(e))
        except ET.ParseError as e:
            log_error(f"QRZ XML parse error during lookup: {e}")
            return Result(False, error=f"XML parse error: {e}")
