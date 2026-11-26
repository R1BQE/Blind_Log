"""Accessible browser controller for the Hamlib Dummy transceiver.

Run run_virtual_transceiver.bat from the Blind_Log project directory.
The Dummy rigctld server listens only on 127.0.0.1:4533.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import webbrowser


ROOT = Path(__file__).resolve().parents[1]
RIG_PORT = 4533
WEB_HOST = "127.0.0.1"
WEB_PORT = 8765
MODES = {
    "USB": 2400,
    "LSB": 2400,
    "CW": 500,
    "CWR": 500,
    "FM": 12000,
    "AM": 6000,
    "RTTY": 500,
    "MFSK": 2000,
    "PKTUSB": 3000,
    "PKTLSB": 3000,
}
PAGE = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blind_Log — виртуальный трансивер</title>
<style>
body { font: 16px system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
label { display: block; margin-top: 1rem; font-weight: 600; }
input, select, button { font: inherit; padding: .55rem; margin-top: .3rem; }
input, select { width: 100%; box-sizing: border-box; }
button { cursor: pointer; margin-right: .5rem; }
#status { margin-top: 1rem; padding: .75rem; border: 1px solid #888; }
.current { margin-top: 1.5rem; }
</style>
</head>
<body>
<main>
<h1>Виртуальный трансивер</h1>
<p>Изменения применяются к Hamlib Dummy. В Blind_Log используйте удалённое
подключение к 127.0.0.1, порт 4533.</p>
<form id="radio-form">
<label for="frequency">Частота, МГц</label>
<input id="frequency" name="frequency" type="number" min="0.01"
       max="300000" step="0.000001" value="145.000000" required>
<label for="mode">Режим Hamlib</label>
<select id="mode" name="mode">
<option value="USB">USB (в журнале SSB)</option>
<option value="LSB">LSB (в журнале SSB)</option>
<option value="CW">CW</option>
<option value="CWR">CW reverse</option>
<option value="FM" selected>FM</option>
<option value="AM">AM</option>
<option value="RTTY">RTTY</option>
<option value="MFSK">MFSK</option>
<option value="PKTUSB">Packet USB</option>
<option value="PKTLSB">Packet LSB</option>
</select>
<p><button type="submit">Применить частоту и режим</button>
<button type="button" id="refresh">Обновить состояние</button></p>
</form>
<section class="current" aria-labelledby="current-heading">
<h2 id="current-heading">Состояние трансивера</h2>
<p id="current-frequency">Частота: загружается</p>
<p id="current-mode">Режим: загружается</p>
</section>
<div id="status" role="status" aria-live="polite">Запуск интерфейса…</div>
</main>
<script>
const form = document.getElementById("radio-form");
const statusBox = document.getElementById("status");
async function refreshState() {
  try {
    const response = await fetch("/api/state");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Ошибка чтения");
    document.getElementById("current-frequency").textContent =
      "Частота: " + data.frequency_mhz + " МГц";
    document.getElementById("current-mode").textContent =
      "Режим: " + data.mode + ", полоса: " + data.bandwidth + " Гц";
    statusBox.textContent = "Связь с виртуальным трансивером работает.";
  } catch (error) {
    statusBox.textContent = "Ошибка: " + error.message;
  }
}
form.addEventListener("submit", async event => {
  event.preventDefault();
  const payload = {
    frequency_mhz: document.getElementById("frequency").value,
    mode: document.getElementById("mode").value
  };
  statusBox.textContent = "Применение настроек…";
  try {
    const response = await fetch("/api/apply", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Ошибка применения");
    statusBox.textContent = "Настройки применены.";
    await refreshState();
  } catch (error) {
    statusBox.textContent = "Ошибка: " + error.message;
  }
});
document.getElementById("refresh").addEventListener("click", refreshState);
refreshState();
setInterval(refreshState, 2000);
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
                value = reader.readline()
                if not value:
                    raise RuntimeError("rigctld закрывает соединение")
                result.append(value.strip())
            return result

    def state(self):
        frequency = float(self.command("f")[0])
        mode, bandwidth = self.command("m", 2)
        if mode.startswith("RPRT") or bandwidth.startswith("RPRT"):
            raise RuntimeError("Не удалось получить режим от rigctld")
        return {
            "frequency_mhz": f"{frequency / 1_000_000:.6f}",
            "mode": mode,
            "bandwidth": int(bandwidth),
        }

    def apply(self, frequency_mhz, mode):
        try:
            frequency = float(str(frequency_mhz).replace(",", "."))
        except (TypeError, ValueError):
            raise ValueError("Введите частоту числом в МГц")
        if not 0.01 <= frequency <= 300000:
            raise ValueError("Частота должна быть от 0.01 до 300000 МГц")
        if mode not in MODES:
            raise ValueError("Неизвестный режим")
        result = self.command(f"F {round(frequency * 1_000_000)}")[0]
        if result != "RPRT 0":
            raise RuntimeError(f"rigctld не принял частоту: {result}")
        result = self.command(f"M {mode} {MODES[mode]}")[0]
        if result != "RPRT 0":
            raise RuntimeError(f"rigctld не принял режим: {result}")


def find_rigctld():
    folder = ROOT / "data" / "hamlib"
    candidates = folder.rglob("rigctld.exe") if folder.exists() else ()
    for path in candidates:
        return path
    raise FileNotFoundError(
        "Не найден data\\hamlib\\rigctld.exe. Сначала установите Hamlib "
        "в настройках Blind_Log."
    )


class RequestHandler(BaseHTTPRequestHandler):
    rig = RigClient()

    def _json(self, status, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if urlparse(self.path).path == "/":
            payload = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/api/state":
            try:
                self._json(200, self.rig.state())
            except Exception as error:
                self._json(503, {"error": str(error)})
            return
        self._json(404, {"error": "Страница не найдена"})

    def do_POST(self):
        if self.path != "/api/apply":
            self._json(404, {"error": "Метод не найден"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 4096:
                raise ValueError("Слишком большой запрос")
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            self.rig.apply(data.get("frequency_mhz"), data.get("mode"))
            self._json(200, {"ok": True})
        except Exception as error:
            self._json(400, {"error": str(error)})

    def log_message(self, _format, *_args):
        return


def main():
    rigctld = find_rigctld()
    env = os.environ.copy()
    env["PATH"] = str(rigctld.parent) + os.pathsep + env.get("PATH", "")
    process = subprocess.Popen(
        [str(rigctld), "-m", "1", "-T", "127.0.0.1", "-t", str(RIG_PORT)],
        cwd=str(rigctld.parent), env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    server = None
    try:
        client = RigClient()
        for _ in range(40):
            if process.poll() is not None:
                raise RuntimeError("Не удалось запустить Hamlib rigctld Dummy")
            try:
                client.command("f")
                break
            except OSError:
                time.sleep(0.25)
        else:
            raise RuntimeError("rigctld не открыл порт 4533")
        try:
            client.apply("145.000000", "FM")
        except Exception:
            pass
        server = ThreadingHTTPServer((WEB_HOST, WEB_PORT), RequestHandler)
        url = f"http://{WEB_HOST}:{WEB_PORT}/"
        print("Виртуальный трансивер запущен.")
        print("Blind_Log: удалённое подключение 127.0.0.1, порт 4533.")
        print(f"Веб-интерфейс: {url}")
        try:
            webbrowser.get("chrome").open_new(url)
        except webbrowser.Error:
            webbrowser.open_new(url)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if server is not None:
            server.server_close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Ошибка запуска: {error}", file=sys.stderr)
        input("Нажмите Enter для закрытия…")
