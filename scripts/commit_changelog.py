"""
Коммитит обновлённый changeLog.txt обратно в репозиторий после перевода.
Если файл не изменился — молча завершается без коммита.

Запускается из корня репозитория в GitHub Actions после translate_changelog.py.
"""

import os
import subprocess
import sys


def configure_utf8_stdio():
    """Force UTF-8 for console output on Windows GitHub runners.

    GitHub Actions can run Python with a legacy console code page such as
    cp1252.  In that mode printing Cyrillic status messages raises
    UnicodeEncodeError before the workflow reaches the build step.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


configure_utf8_stdio()


def run(cmd, check=True, mask=None):
    display = ' '.join(
        '***' if mask and mask in arg else arg
        for arg in cmd
    )
    print(f">>> {display}", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout, flush=True)
    if result.stderr.strip():
        print(result.stderr, flush=True)
    print(f"    exit: {result.returncode}", flush=True)
    if check and result.returncode != 0:
        sys.exit(1)
    return result


token = os.environ.get("GITHUB_TOKEN", "")
repo = os.environ.get("GITHUB_REPOSITORY", "")
print(f"GITHUB_REPOSITORY: {repo}", flush=True)
print(f"GITHUB_TOKEN: {'present' if token else 'MISSING'}", flush=True)

run(["git", "status", "--short"])

if token and repo:
    remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"
    run(["git", "remote", "set-url", "origin", remote_url], mask=token)
else:
    print("WARNING: нет токена или репозитория, push не будет работать", flush=True)

run(["git", "config", "user.name", "github-actions[bot]"])
run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
run(["git", "add", "changeLog.txt"])

diff = run(["git", "diff", "--cached", "--stat"], check=False)
diff_quiet = run(["git", "diff", "--cached", "--quiet"], check=False)
if diff_quiet.returncode == 0:
    print("changeLog.txt не изменился — коммит не нужен.", flush=True)
    sys.exit(0)

run(["git", "commit", "-m", "chore: add [EN] translation to changeLog.txt [skip ci]"])
push = run(["git", "push", "origin", "HEAD:main"], check=False)
if push.returncode != 0:
    print("WARNING: push не удался, но продолжаем сборку.", flush=True)

print("Готово.", flush=True)
