"""
Коммитит обновлённый changeLog.txt обратно в репозиторий после перевода.
Если файл не изменился — молча завершается без коммита.

Запускается из корня репозитория в GitHub Actions после translate_changelog.py.
"""

import subprocess
import sys


def run(cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"ERROR: {' '.join(cmd)}\n{result.stderr}")
        sys.exit(1)
    return result


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
