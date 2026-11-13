"""Защита от запуска двух копий бота одновременно.

Если запустить две копии, обе получат одно событие LongPoll
и пользователь увидит два одинаковых ответа.
"""

from __future__ import annotations

import socket

LOCK_PORT = 47653


def acquire_single_instance_lock() -> socket.socket:
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
