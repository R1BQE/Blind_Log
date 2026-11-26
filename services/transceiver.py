"""Optional Hamlib integration for portable Blind Log installations."""
import hashlib
import io
import os
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import zipfile

import requests

from common.utils import get_app_path

GITHUB_RELEASES_API = "https://api.github.com/repos/Hamlib/Hamlib/releases/latest"
REQUEST_TIMEOUT = (10, 90)


class HamlibError(RuntimeError):
    """Raised when Hamlib cannot be installed or contacted."""


def get_hamlib_dir():
    return os.path.join(get_app_path(), "data", "hamlib")


def find_hamlib_executable(name):
    filename = name if name.lower().endswith(".exe") else name + ".exe"
    root = get_hamlib_dir()
    if not os.path.isdir(root):
        return None
    for current, _directories, files in os.walk(root):
        for item in files:
            if item.lower() == filename.lower():
                return os.path.join(current, item)
    return None


def get_installed_version():
    marker = os.path.join(get_hamlib_dir(), "BLIND_LOG_HAMLIB_VERSION.txt")
    try:
        with open(marker, "r", encoding="utf-8") as stream:
            value = stream.read().strip()
            if value:
                return value
    except OSError:
        pass
    executable = find_hamlib_executable("rigctld")
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, "--version"], cwd=os.path.dirname(executable),
            capture_output=True, text=True, timeout=10, check=False,
        )
        match = re.search(r"\b(\d+\.\d+(?:\.\d+)?)\b",
                          (result.stdout or "") + " " + (result.stderr or ""))
        return match.group(1) if match else None
    except (OSError, subprocess.SubprocessError):
        return None


def is_hamlib_installed():
    return find_hamlib_executable("rigctld") is not None


def _safe_extract(archive, destination):
    """Extract ZIP members while rejecting path traversal entries."""
    destination = os.path.realpath(destination)
    os.makedirs(destination, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(archive)) as zip_stream:
        for member in zip_stream.infolist():
            target = os.path.realpath(os.path.join(destination, member.filename))
            if target != destination and not target.startswith(destination + os.sep):
                raise HamlibError("The Hamlib archive contains an unsafe path")
        zip_stream.extractall(destination)


def _download_response(url, session, progress_callback=None):
    response = session.get(url, stream=True, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    chunks, downloaded = [], 0
    total = int(response.headers.get("Content-Length", 0) or 0)
    for chunk in response.iter_content(chunk_size=128 * 1024):
        if chunk:
            chunks.append(chunk)
            downloaded += len(chunk)
            if progress_callback:
                progress_callback(downloaded, total)
    return b"".join(chunks)


def _parse_sha256_checksum(checksum_text, archive_name):
    """Read the checksum belonging to the requested archive.

    Hamlib publishes one checksum file per Windows architecture containing
    hashes for both the ZIP and self-extracting EXE. Never assume the first
    hash belongs to the ZIP.
    """
    hashes = []
    for line in str(checksum_text).splitlines():
        match = re.match(
            r"^\s*([0-9a-fA-F]{64})(?:\s+[* ]?(.+?))?\s*$", line
        )
        if match:
            digest, filename = match.groups()
            hashes.append((
                digest.lower(),
                os.path.basename(filename.strip()) if filename else ""
            ))
    for digest, filename in hashes:
        if filename and filename.lower() == os.path.basename(archive_name).lower():
            return digest
    if len(hashes) == 1 and not hashes[0][1]:
        return hashes[0][0]
    raise HamlibError(
        f"Could not find a SHA-256 entry for {archive_name} in the official checksum file"
    )


def download_latest_hamlib(progress_callback=None, session=None):
    """Download and atomically install the official portable Windows ZIP."""
    session = session or requests.Session()
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "Blind-Log-Hamlib-Installer"}
    response = session.get(GITHUB_RELEASES_API, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    release = response.json()
    version = str(release.get("tag_name", "")).strip().lstrip("v")
    if not version:
        raise HamlibError("GitHub did not return a Hamlib release version")
    architecture = "w64" if struct.calcsize("P") * 8 >= 64 else "w32"
    archive_name = f"hamlib-{architecture}-{version}.zip"
    checksum_name = f"SHA256SUM-{architecture}-{version}"
    assets = {item.get("name"): item for item in release.get("assets", [])}
    archive_asset, checksum_asset = assets.get(archive_name), assets.get(checksum_name)
    if not archive_asset or not checksum_asset:
        raise HamlibError(
            f"Official Hamlib release {version} has no required Windows ZIP "
            f"({archive_name}) or SHA-256 checksum"
        )
    checksum_response = session.get(
        checksum_asset["browser_download_url"], headers=headers, timeout=REQUEST_TIMEOUT
    )
    checksum_response.raise_for_status()
    expected_hash = _parse_sha256_checksum(
        checksum_response.text, archive_name
    )
    archive_bytes = _download_response(
        archive_asset["browser_download_url"], session, progress_callback
    )
    actual_hash = hashlib.sha256(archive_bytes).hexdigest()
    if actual_hash != expected_hash:
        raise HamlibError("The downloaded Hamlib ZIP failed SHA-256 verification")

    data_dir = os.path.dirname(get_hamlib_dir())
    os.makedirs(data_dir, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".hamlib-stage-", dir=data_dir)
    target, backup = get_hamlib_dir(), get_hamlib_dir() + ".previous"
    try:
        _safe_extract(archive_bytes, staging)
        found = any(
            "rigctld.exe" in {name.lower() for name in files}
            for _root, _dirs, files in os.walk(staging)
        )
        if not found:
            raise HamlibError("The ZIP archive does not contain rigctld.exe")
        with open(os.path.join(staging, "BLIND_LOG_HAMLIB_VERSION.txt"),
                  "w", encoding="utf-8") as marker:
            marker.write(version)
        if os.path.exists(backup):
            shutil.rmtree(backup, ignore_errors=True)
        if os.path.exists(target):
            os.replace(target, backup)
        try:
            os.replace(staging, target)
            staging = None
        except Exception:
            if os.path.exists(backup) and not os.path.exists(target):
                os.replace(backup, target)
            raise
        if os.path.exists(backup):
            shutil.rmtree(backup, ignore_errors=True)
        return {"version": version, "archive": archive_name,
                "path": target, "sha256": actual_hash}
    finally:
        if staging and os.path.exists(staging):
            shutil.rmtree(staging, ignore_errors=True)


def list_hamlib_models():
    """Return (model_id, display_line) pairs from the official rig list."""
    executable = find_hamlib_executable("rigctl") or find_hamlib_executable("rigctld")
    if not executable:
        return []
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(executable) + os.pathsep + env.get("PATH", "")
    try:
        result = subprocess.run(
            [executable, "-l"], cwd=os.path.dirname(executable), env=env,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=20, check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise HamlibError(f"Could not read Hamlib model list: {error}") from error
    models = []
    for line in (result.stdout or "").splitlines():
        match = re.match(r"^\s*(\d+)\s+(.+?)\s*$", line)
        if match:
            models.append((match.group(1), match.group(2)))
    if not models and result.returncode:
        raise HamlibError((result.stderr or "Empty Hamlib model list").strip())
    return models


def list_serial_ports():
    try:
        from serial.tools import list_ports
        return [(item.device, item.description or item.device)
                for item in list_ports.comports()]
    except ImportError:
        return []


class RigctldClient:
    """Small client for rigctld's line-oriented TCP protocol."""
    def __init__(self, host="127.0.0.1", port=4532, timeout=2.0):
        self.host, self.port, self.timeout = str(host).strip(), int(port), float(timeout)

    def _command(self, command, line_count=1):
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as conn:
                conn.settimeout(self.timeout)
                conn.sendall((command + "\n").encode("ascii"))
                reader = conn.makefile("r", encoding="ascii", newline="\n")
                lines = []
                for _ in range(line_count):
                    line = reader.readline()
                    if not line:
                        raise HamlibError("rigctld closed the connection")
                    lines.append(line.strip())
                return lines
        except (OSError, ValueError) as error:
            raise HamlibError(f"Cannot communicate with rigctld: {error}") from error

    def get_frequency(self):
        line = self._command("f")[0]
        try:
            value = float(line)
        except ValueError as error:
            raise HamlibError(f"Invalid frequency response: {line}") from error
        if value <= 0:
            raise HamlibError(f"Transceiver returned invalid frequency: {line}")
        return value

    def get_mode(self):
        mode, passband = self._command("m", 2)
        if mode.startswith("RPRT") or passband.startswith("RPRT"):
            raise HamlibError(f"Could not read transceiver mode: {mode} {passband}")
        try:
            bandwidth = int(passband)
        except ValueError:
            bandwidth = 0
        return {"mode": mode.upper(), "bandwidth": bandwidth}

    def get_snapshot(self):
        return {"frequency_hz": self.get_frequency(), **self.get_mode()}

    def get_level(self, token):
        token = str(token).strip().upper()
        if not re.fullmatch(r"[A-Z0-9_]+", token):
            raise HamlibError("Invalid Hamlib level token")
        line = self._command(f"l {token}")[0]
        if line.startswith("RPRT"):
            raise HamlibError(f"Hamlib cannot read {token}: {line}")
        try:
            return float(line)
        except ValueError as error:
            raise HamlibError(f"Invalid {token} response: {line}") from error

    def set_level(self, token, value):
        token = str(token).strip().upper()
        if not re.fullmatch(r"[A-Z0-9_]+", token):
            raise HamlibError("Invalid Hamlib level token")
        value = str(value).strip()
        if not value or any(char in value for char in "\r\n"):
            raise HamlibError("Invalid Hamlib level value")
        result = self._command(f"L {token} {value}")[0]
        if result != "RPRT 0":
            raise HamlibError(f"Hamlib could not set {token}: {result}")
        return True

    def get_power(self):
        errors = []
        for token in ("RFPOWER_METER_WATTS", "RFPOWER_METER"):
            try:
                return {"token": token, "value": self.get_level(token)}
            except HamlibError as error:
                errors.append(str(error))
        raise HamlibError("POWER_METER_UNSUPPORTED")


class TransceiverController:
    """Own the optional local rigctld process and expose CAT read operations."""
    def __init__(self):
        self.process, self.client = None, None

    def configure(self, settings):
        self.stop()
        if str(settings.get("use_hamlib", "0")) != "1":
            return False
        port = int(settings.get("transceiver_port", "4532") or 4532)
        if settings.get("transceiver_connection", "local") == "remote":
            host = str(settings.get("transceiver_host", "127.0.0.1")).strip()
            if not host:
                raise HamlibError("The rigctld server address is empty")
            self.client = RigctldClient(host, port)
            return True
        executable = find_hamlib_executable("rigctld")
        if not executable:
            raise HamlibError("Hamlib is not installed; download it in Transceiver settings")
        model_id = str(settings.get("transceiver_model_id", "")).strip()
        serial_port = str(settings.get("transceiver_com_port", "")).strip()
        if not model_id:
            raise HamlibError("Select a transceiver model in Settings")
        # Hamlib model 1 is the built-in Dummy backend. It simulates a radio
        # and does not use a serial/COM port or a CAT baud rate.
        is_dummy = model_id == "1"
        if not is_dummy and not serial_port:
            raise HamlibError("Select a COM port for the selected transceiver model")
        binary_dir = os.path.dirname(executable)
        env = os.environ.copy()
        env["PATH"] = binary_dir + os.pathsep + env.get("PATH", "")
        args = [executable, "-m", model_id]
        if not is_dummy:
            args.extend([
                "-r", serial_port,
                "-s", str(settings.get("transceiver_baudrate", "9600")),
            ])
        args.extend(["-T", "127.0.0.1", "-t", str(port)])
        try:
            self.process = subprocess.Popen(
                args, cwd=binary_dir, env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as error:
            raise HamlibError(f"Could not start rigctld: {error}") from error
        self.client = RigctldClient("127.0.0.1", port)
        return True

    def is_configured(self):
        return self.client is not None

    def _check(self):
        if self.client is None:
            raise HamlibError("Transceiver control is not enabled")
        if self.process is not None and self.process.poll() is not None:
            raise HamlibError("The local rigctld process has stopped")

    def get_frequency(self):
        self._check()
        return self.client.get_frequency()

    def get_mode(self):
        self._check()
        return self.client.get_mode()

    def get_snapshot(self):
        self._check()
        return self.client.get_snapshot()

    def get_power(self):
        self._check()
        return self.client.get_power()

    def stop(self):
        process, self.process, self.client = self.process, None, None
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
                process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                pass


def frequency_to_mhz(frequency_hz):
    return f"{float(frequency_hz) / 1_000_000:.6f}"


def normalize_mode_for_log(mode):
    normalized = str(mode or "").upper()
    if normalized in ("USB", "LSB", "DSB", "LSB-D", "USB-D"):
        return "SSB"
    if normalized in ("AM", "FM", "CW", "CWR", "RTTY", "MFSK", "PKTUSB", "PKTLSB"):
        if normalized == "CWR":
            return "CW"
        if normalized in ("PKTUSB", "PKTLSB"):
            return "MFSK"
        return normalized
    return None
