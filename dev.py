"""Локальный запуск бота и веб-сервера одной командой.

    python dev.py

Запускает два процесса:
- manage.py runbot    — бот ВКонтакте;
- manage.py runserver — админка и веб-кабинет.

Ctrl+C останавливает оба.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = BASE_DIR / ".venv" / (
    "Scripts/python.exe" if os.name == "nt" else "bin/python"
)
PYTHON = VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)

COMMANDS = (
    ("бот", [str(PYTHON), "manage.py", "runbot"]),
    ("веб", [str(PYTHON), "manage.py", "runserver", "127.0.0.1:8000", "--noreload"]),
)


def main() -> int:
    processes: list[tuple[str, subprocess.Popen]] = []

    try:
        for name, command in COMMANDS:
            print(f"→ {name}: {' '.join(command)}")
            processes.append((name, subprocess.Popen(command, cwd=BASE_DIR)))

        print("Ctrl+C — остановить оба процесса.")
        while True:
            for name, process in processes:
                code = process.poll()
                if code is not None:
                    print(f"{name} завершился с кодом {code}")
                    return code
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nОстанавливаю…")
        return 0
    finally:
        for _, process in processes:
            if process.poll() is None:
                process.terminate()
        for _, process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
