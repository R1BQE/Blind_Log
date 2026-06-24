"""
Коммитит обновлённый changeLog.txt обратно в репозиторий после перевода.
Если файл не изменился — молча завершается без коммита.

Запускается из корня репозитория в GitHub Actions после translate_changelog.py.
"""

import os
import subprocess
import sys


def run(cmd, check=True):
    print(f">>> {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    print(f"    exit code: {result.returncode}")
    if check and result.returncode != 0:
        print(f"ERROR: команда завершилась с ошибкой")
        sys.exit(1)
    return result


token = os.environ.get("GITHUB_TOKEN", "")
repo = os.environ.get("GITHUB_REPOSITORY", "")
print(f"GITHUB_REPOSITORY: {repo}")
print(f"GITHUB_TOKEN present: {'yes' if token else 'NO - missing!'}")

if token and repo:
    remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"
    run(["git", "remote", "set-url", "origin", remote_url])
else:
    print("WARNING: GITHUB_TOKEN или GITHUB_REPOSITORY не заданы, push может не сработать")

run(["git", "config", "user.name", "github-actions[bot]"])
run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
run(["git", "add", "changeLog.txt"])

diff = run(["git", "diff", "--cached", "--quiet"], check=False)
if diff.returncode == 0:
    print("changeLog.txt не изменился, коммит не нужен.")
    sys.exit(0)

run(["git", "commit", "-m", "chore: add [EN] translation to changeLog.txt [skip ci]"])
run(["git", "push", "origin", "HEAD:main"])
print("changeLog.txt успешно закоммичен.")
