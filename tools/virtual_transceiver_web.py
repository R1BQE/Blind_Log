"""Accessible browser controller for a Hamlib Dummy transceiver."""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
RIG_PORT = 4533
WEB_HOST = "127.0.0.1"
WEB_PORT = 8765
MODES = {
    "USB": 2400, "LSB": 2400, "CW": 500, "CWR": 500,
    "FM": 12000, "AM": 6000, "RTTY": 500, "MFSK": 2000,
    "PKTUSB": 3000, "PKTLSB": 3000,
}
PAGE = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blind_Log — виртуальный трансивер</title>
<style>
body { font: 16px system-ui,sans-serif; max-width: 48rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
label { display:block; margin-top: .8rem; font-weight:600; }
input,select,button { font:inherit; padding:.5rem; margin-top:.25rem; }
input,select { max-width:100%; box-sizing:border-box; }
input[type=number],input[type=text] { width:100%; }
button { cursor:pointer; margin:.5rem .5rem .5rem 0; }
fieldset { margin:1rem 0; padding:.8rem; }
.control-row { border-bottom:1px solid #aaa; padding:.5rem 0; }
.control-row:last-child { border:0; }
.control-row button { margin-left:.5rem; }
.hint { font-size:.9rem; }
#status { margin-top:1rem; padding:.75rem; border:1px solid #888; }
</style>
</head>
<body>
<main>
<h1>Виртуальный трансивер</h1>
<p>Изменения применяются к Hamlib Dummy. В Blind_Log используйте удалённое подключение к 127.0.0.1, порт 4533.</p>
<form id="radio-form">
<label for="frequency">Частота, МГц</label>
<input id="frequency" type="number" min="0.01" max="300000" step="0.000001" value="145.000000" required>
<label for="mode">Режим Hamlib</label>
<select id="mode">
<option value="USB">USB</option><option value="LSB">LSB</option>
<option value="CW">CW</option><option value="CWR">CW reverse</option>
<option value="FM" selected>FM</option><option value="AM">AM</option>
<option value="RTTY">RTTY</option><option value="MFSK">MFSK</option>
<option value="PKTUSB">Packet USB</option><option value="PKTLSB">Packet LSB</option>
</select>
<label for="bandwidth">Полоса, Гц (0 — полоса по умолчанию)</label>
<input id="bandwidth" type="number" min="0" step="1" value="0">
<p><button type="submit">Применить частоту, режим и полосу</button>
<button type="button" id="refresh">Обновить состояние</button></p>
</form>
<section aria-labelledby="current-heading">
<h2 id="current-heading">Состояние трансивера</h2>
<p id="current-frequency">Частота: загружается</p>
<p id="current-mode">Режим: загружается</p>
<p id="current-vfo">VFO: загружается</p>
</section>
<section aria-labelledby="vfo-heading">
<h2 id="vfo-heading">Выбор VFO</h2>
<label for="vfo-select">Рабочий VFO</label>
<select id="vfo-select"><option value="">Не поддерживается</option></select>
<button type="button" id="apply-vfo">Переключить VFO</button>
</section>
<section aria-labelledby="controls-heading">
<h2 id="controls-heading">Дополнительные настройки Hamlib</h2>
<p class="hint">Здесь автоматически отображаются параметры, которые Hamlib объявляет доступными для выбранной модели. Состав зависит от трансивера. Для числовых параметров вводите значение, затем нажимайте соответствующую кнопку.</p>
<div id="dynamic-controls">Получение списка возможностей…</div>
</section>
<div id="status" role="status" aria-live="polite">Запуск интерфейса…</div>
</main>
<script>
const statusBox = document.getElementById("status");
function showStatus(message) { statusBox.textContent = message; }
async function api(path, options) {
  const response = await fetch(path, options || {});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Ошибка запроса");
  return data;
}
async function refreshState() {
  try {
    const data = await api("/api/state");
    document.getElementById("current-frequency").textContent = "Частота: " + data.frequency_mhz + " МГц";
    document.getElementById("current-mode").textContent = "Режим: " + data.mode + ", полоса: " + data.bandwidth + " Гц";
    document.getElementById("bandwidth").value = data.bandwidth;
    document.getElementById("current-vfo").textContent = "VFO: " + (data.vfo || "неизвестен");
    showStatus("Связь с виртуальным трансивером работает.");
  } catch (error) { showStatus("Ошибка: " + error.message); }
}
document.getElementById("radio-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    await api("/api/apply", {method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({frequency_mhz:document.getElementById("frequency").value,
                           mode:document.getElementById("mode").value,
                           bandwidth:document.getElementById("bandwidth").value})});
    showStatus("Частота и режим применены.");
    await refreshState();
  } catch (error) { showStatus("Ошибка: " + error.message); }
});
function makeControlRow(category, token, current, canRead) {
  const row = document.createElement("div");
  row.className = "control-row";
  const label = document.createElement("label");
  label.textContent = token + (canRead ? " (текущее значение доступно)" : " (только установка)");
  const input = document.createElement(category === "functions" ? "input" : "input");
  input.id = "setting-" + category + "-" + token;
  if (category === "functions") {
    input.type = "checkbox";
    input.checked = current === "1" || current === "true";
  } else {
    input.type = "text";
    input.value = current === null || current === undefined ? "" : String(current);
    input.autocomplete = "off";
  }
  label.htmlFor = input.id;
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "Применить " + token;
  button.addEventListener("click", async () => {
    const value = category === "functions" ? (input.checked ? "1" : "0") : input.value.trim();
    if (!value && category !== "functions") { showStatus("Введите значение для " + token); input.focus(); return; }
    try {
      await api("/api/control", {method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({category:category,token:token,value:value})});
      showStatus("Параметр " + token + " применён.");
      await loadControls();
    } catch (error) { showStatus("Не удалось применить " + token + ": " + error.message); }
  });
  row.appendChild(label); row.appendChild(input); row.appendChild(button);
  return row;
}
async function loadControls() {
  const container = document.getElementById("dynamic-controls");
  container.textContent = "Получение списка возможностей…";
  try {
    const data = await api("/api/capabilities");
    const modeSelect = document.getElementById("mode");
    if (data.modes && data.modes.length) {
      const selectedMode = modeSelect.value;
      modeSelect.replaceChildren();
      for (const mode of data.modes) {
        const option = document.createElement("option");
        option.value = mode;
        option.textContent = mode;
        modeSelect.appendChild(option);
      }
      if (data.modes.includes(selectedMode)) modeSelect.value = selectedMode;
    }
    const vfoSelect = document.getElementById("vfo-select");
    if (vfoSelect && data.vfos && data.vfos.length) {
      vfoSelect.replaceChildren();
      for (const vfo of data.vfos) {
        const option = document.createElement("option");
        option.value = vfo; option.textContent = vfo; vfoSelect.appendChild(option);
      }
      if (data.current_vfo && data.vfos.includes(data.current_vfo)) vfoSelect.value = data.current_vfo;
    }
    container.replaceChildren();
    const groups = [
      ["levels","Уровни и регулировки"],
      ["functions","Функции (включение и выключение)"],
      ["parameters","Параметры радио"]
    ];
    for (const [category,title] of groups) {
      const setTokens = data[category].set || [];
      const getValues = data[category].values || {};
      const getTokens = data[category].get || [];
      if (!setTokens.length && !getTokens.length) continue;
      const fieldset = document.createElement("fieldset");
      const legend = document.createElement("legend"); legend.textContent = title; fieldset.appendChild(legend);
      for (const token of setTokens) {
        fieldset.appendChild(makeControlRow(category,token,getValues[token],getTokens.includes(token)));
      }
      for (const token of getTokens) {
        if (!setTokens.includes(token)) {
          const p = document.createElement("p");
          p.textContent = token + ": " + (getValues[token] === undefined ? "значение недоступно" : getValues[token]);
          fieldset.appendChild(p);
        }
      }
      container.appendChild(fieldset);
    }
    if (!container.children.length) container.textContent = "Hamlib не сообщил дополнительных настраиваемых параметров для этой модели.";
  } catch (error) {
    container.textContent = "Не удалось получить возможности трансивера: " + error.message;
  }
}
document.getElementById("apply-vfo").addEventListener("click",async () => {
  const value = document.getElementById("vfo-select").value;
  if (!value) { showStatus("Переключение VFO не поддерживается этой моделью."); return; }
  try {
    await api("/api/control",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({category:"vfo",value:value})});
    showStatus("VFO переключён на " + value + ".");
    await refreshState();
  } catch (error) { showStatus("Не удалось переключить VFO: " + error.message); }
});
document.getElementById("refresh").addEventListener("click",refreshState);
refreshState();
loadControls();
setInterval(refreshState,2000);
</script>
</body>
</html>
"""


class RigClient:
    def __init__(self, host="127.0.0.1", port=RIG_PORT):
        self.host, self.port = host, port

    def command(self, command, lines=1):
        with socket.create_connection((self.host, self.port), timeout=2) as conn:
            conn.settimeout(2)
            conn.sendall((command + "\n").encode("ascii"))
            reader = conn.makefile("r", encoding="ascii")
            result = []
            for _ in range(lines):
                line = reader.readline()
                if not line:
                    raise RuntimeError("rigctld закрыл соединение")
                result.append(line.strip())
            return result[0] if lines == 1 else result

    def query_tokens(self, command):
        result = self.command(command)
        if result.startswith("RPRT"):
            return []
        return [token for token in result.split() if re.fullmatch(r"[A-Z0-9_]+", token)]

    def get_tokens(self, prefix):
        return self.query_tokens(prefix + " ?")

    def get_value(self, prefix, token):
        result = self.command(prefix + " " + token)
        if result.startswith("RPRT"):
            return None
        return result

    def state(self):
        frequency = float(self.command("f"))
        mode, bandwidth = self.command("m", 2)
        if mode.startswith("RPRT") or bandwidth.startswith("RPRT"):
            raise RuntimeError("Не удалось получить режим от rigctld")
        try:
            vfo = self.command("v")
            if vfo.startswith("RPRT"):
                vfo = ""
        except Exception:
            vfo = ""
        return {"frequency_mhz":f"{frequency / 1_000_000:.6f}",
                "mode":mode,"bandwidth":int(bandwidth),"vfo":vfo}

    def apply(self, frequency_mhz, mode, bandwidth=None):
        try:
            frequency = float(str(frequency_mhz).replace(",", "."))
        except (TypeError, ValueError):
            raise ValueError("Введите частоту числом в МГц")
        if not 0.01 <= frequency <= 300000:
            raise ValueError("Частота должна быть от 0.01 до 300000 МГц")
        supported_modes = self.get_tokens("M")
        if mode not in supported_modes:
            raise ValueError("Этот режим не поддерживается выбранной моделью Hamlib")
        result = self.command(f"F {round(frequency * 1_000_000)}")
        if result != "RPRT 0":
            raise RuntimeError(f"rigctld не принял частоту: {result}")
        try:
            passband = int(bandwidth) if bandwidth not in (None, "") else MODES.get(mode, 0)
        except (TypeError, ValueError):
            raise ValueError("Ширина полосы должна быть целым числом")
        if passband < 0:
            raise ValueError("Ширина полосы не может быть отрицательной")
        result = self.command(f"M {mode} {passband}")
        if result != "RPRT 0":
            raise RuntimeError(f"rigctld не принял режим: {result}")

    def capabilities(self):
        categories = {
            "levels":("L","l"),
            "functions":("U","u"),
            "parameters":("P","p"),
        }
        result = {"modes": self.get_tokens("M"), "vfos": self.get_tokens("V")}
        try:
            result["current_vfo"] = self.command("v")
        except Exception:
            result["current_vfo"] = ""
        for category,(set_prefix,get_prefix) in categories.items():
            set_tokens = self.get_tokens(set_prefix)
            get_tokens = self.get_tokens(get_prefix)
            values = {}
            for token in get_tokens:
                value = self.get_value(get_prefix,token)
                if value is not None:
                    values[token] = value
            result[category] = {"set":set_tokens,"get":get_tokens,"values":values}
        return result

    def set_control(self, category, token, value):
        prefixes = {"levels":"L","functions":"U","parameters":"P"}
        if category == "vfo":
            value = str(value).strip()
            if not re.fullmatch(r"[A-Za-z0-9_]+", value):
                raise ValueError("Некорректное значение VFO")
            result = self.command("V " + value)
            if result != "RPRT 0":
                raise RuntimeError(f"Hamlib не смог переключить VFO: {result}")
            return
        if category not in prefixes or not re.fullmatch(r"[A-Z0-9_]+",str(token).upper()):
            raise ValueError("Неизвестная категория или параметр")
        token = str(token).upper()
        value = str(value).strip()
        if not value or any(char.isspace() for char in value):
            raise ValueError("Введите одно значение без пробелов")
        result = self.command(f"{prefixes[category]} {token} {value}")
        if result != "RPRT 0":
            raise RuntimeError(f"Hamlib вернул ошибку: {result}")


def find_rigctld():
    folder = ROOT / "data" / "hamlib"
    candidates = folder.rglob("rigctld.exe") if folder.exists() else ()
    for path in candidates:
        return path
    raise FileNotFoundError("Не найден data\\hamlib\\rigctld.exe. Сначала установите Hamlib в настройках Blind_Log.")


class RequestHandler(BaseHTTPRequestHandler):
    rig = RigClient()

    def _json(self,status,data):
        payload=json.dumps(data,ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(payload)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/":
            payload=PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif path=="/api/state":
            try: self._json(200,self.rig.state())
            except Exception as error: self._json(503,{"error":str(error)})
        elif path=="/api/capabilities":
            try: self._json(200,self.rig.capabilities())
            except Exception as error: self._json(503,{"error":str(error)})
        else:
            self._json(404,{"error":"Страница не найдена"})

    def do_POST(self):
        path=urlparse(self.path).path
        if path not in ("/api/apply","/api/control"):
            self._json(404,{"error":"Метод не найден"})
            return
        try:
            length=int(self.headers.get("Content-Length","0"))
            if length>8192: raise ValueError("Слишком большой запрос")
            data=json.loads(self.rfile.read(length).decode("utf-8"))
            if path=="/api/apply":
                self.rig.apply(data.get("frequency_mhz"),data.get("mode"),data.get("bandwidth"))
            else:
                self.rig.set_control(data.get("category"),data.get("token"),data.get("value"))
            self._json(200,{"ok":True})
        except Exception as error:
            self._json(400,{"error":str(error)})

    def log_message(self,_format,*_args):
        return


def main():
    rigctld=find_rigctld()
    env=os.environ.copy()
    env["PATH"]=str(rigctld.parent)+os.pathsep+env.get("PATH","")
    process=subprocess.Popen(
        [str(rigctld),"-m","1","-T","127.0.0.1","-t",str(RIG_PORT)],
        cwd=str(rigctld.parent),env=env,stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),
    )
    server=None
    try:
        client=RigClient()
        for _ in range(40):
            if process.poll() is not None:
                raise RuntimeError("Не удалось запустить Hamlib rigctld Dummy")
            try:
                client.command("f")
                break
            except OSError:
                time.sleep(.25)
        else:
            raise RuntimeError("rigctld не открыл порт 4533")
        try: client.apply("145.000000","FM")
        except Exception: pass
        server=ThreadingHTTPServer((WEB_HOST,WEB_PORT),RequestHandler)
        url=f"http://{WEB_HOST}:{WEB_PORT}/"
        print("Виртуальный трансивер запущен.")
        print("Blind_Log: удалённое подключение 127.0.0.1, порт 4533.")
        print(f"Веб-интерфейс: {url}")
        try: webbrowser.get("chrome").open_new(url)
        except webbrowser.Error: webbrowser.open_new(url)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if server is not None: server.server_close()
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired: process.kill()


if __name__=="__main__":
    try: main()
    except Exception as error:
        print(f"Ошибка запуска: {error}",file=sys.stderr)
        input("Нажмите Enter для закрытия…")
