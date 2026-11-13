"""Эхо-бот: первый этап обучения.

Что делает:
- подключается к сообществу по LongPoll;
- на /start или «Начать» здоровается;
- на любой текст отвечает «Ты написал: ...».

Запуск:
    python main.py
"""

from __future__ import annotations

import logging
import os
import socket
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from vk import VK


# Порт-«замок»: пока первый экземпляр держит его, второй не запустится.
LOCK_PORT = 47653

# Читает файл .env рядом с main.py и кладёт значения в переменные окружения.
load_dotenv()

LOG_FILE = Path(__file__).with_name("bot.log")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        # Лог всегда в UTF-8 и рядом с кодом — не зависит от оболочки.
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
# urllib3 логирует каждый HTTP-запрос — для учёбы это шум.
logging.getLogger("urllib3").setLevel(logging.WARNING)
log = logging.getLogger(__name__)
counter = 0


def main() -> None:
    lock = acquire_single_instance_lock()

    token = os.getenv("VK_TOKEN", "").strip()
    group_raw = os.getenv("VK_GROUP_ID", "").strip()

    if not token or not group_raw:
        raise SystemExit("Заполните VK_TOKEN и VK_GROUP_ID в файле .env")

    vk = VK(token, int(group_raw))
    log.info(
        "Бот запущен для сообщества %s (PID %s). Жду сообщения…",
        group_raw,
        os.getpid(),
    )

    try:
        for update in vk.long_poll():
            handle_update(vk, update)
    except KeyboardInterrupt:
        log.info("Остановлено вручную")
    finally:
        lock.close()


def acquire_single_instance_lock() -> socket.socket:
    """Занимает локальный порт. Второй запуск получит ошибку и выйдет.

    Зачем: если запустить две копии, обе получат одно событие LongPoll
    и пользователь увидит два одинаковых ответа.
    """
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock.bind(("127.0.0.1", LOCK_PORT))
        lock.listen(1)
    except OSError:
        lock.close()
        raise SystemExit(
            "Бот уже запущен в другом окне. Закройте его и запустите снова."
        ) from None
    return lock


def handle_update(vk: VK, update: dict) -> None:
    """Обрабатывает одно событие из LongPoll."""

    global counter  # Для отладки потом убрать!!!

    event_type = update.get("type")
    log.debug("Событие: %s", event_type)

    # Нас интересуют только новые сообщения.
    if event_type != "message_new":
        return

    message = update["object"]["message"]

    # Сообщения самого сообщества (from_id < 0) не обрабатываем.
    if message["from_id"] <= 0:
        return

    text = (message.get("text") or "").strip()
    peer_id = message["peer_id"]

    log.debug("Сообщение от %s: %r", message["from_id"], text)

    if text.casefold() in {"/start", "начать", "start"}:
        reply = "Привет! Я бот, я тут что бы Вам помогать."
    elif text.casefold() in {"/time", "время", "time"}:
        reply = f"Время: {datetime.now().strftime('%H:%M:%S')}"

    # Для отладки потом убрать!!! --------------
    elif text == '+':
        counter += 1
        reply = f'Счётчик: {counter}'
    # ------------------------------------------

    elif text:
        reply = f"Ты написал: {text}"
    else:
        reply = "Я понимаю только текст."

    log.debug("Ответ в %s: %r", peer_id, reply)
    vk.send_message(peer_id, reply)


if __name__ == "__main__":
    main()
