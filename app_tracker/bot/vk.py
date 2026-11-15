"""Транспортный слой / клиент API.

Отвечает за две вещи «как поговорить с ВК»:
- вызов методов API через https://api.vk.com/method;
- получение событий через LongPoll.

Этот модуль можно запустить и протестировать отдельно от Django.
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from typing import Any, Iterator

import requests

log = logging.getLogger(__name__)

# Все методы ВК вызываются по одному адресу: https://api.vk.com/method/<имя>
API_URL = "https://api.vk.com/method"

# Версия API фиксируется, чтобы ответы не менялись неожиданно.
API_VERSION = "5.199"

# Сколько секунд ВК держит LongPoll-соединение, если событий нет.
LONG_POLL_WAIT = 25

# Пауза перед переподключением, если сеть или ВК недоступны.
RETRY_DELAY = 5

# Сколько подряд сетевых ошибок терпим, прежде чем взять новую сессию LongPoll.
# Новую сессию берём только в крайнем случае: у неё свежий ts, и события,
# пришедшие во время обрыва, могут потеряться.
SESSION_RETRIES = 3


class VK:
    def __init__(self, token: str, group_id: int, *, api_version: str = API_VERSION) -> None:
        self.token = token
        self.group_id = group_id
        self.api_version = api_version
        # Session переиспользует TCP-соединение — так быстрее, чем requests.post каждый раз.
        self.session = requests.Session()

    def call(self, method: str, **params: Any) -> Any:
        """Вызывает любой метод API и возвращает поле `response` некая точка входа в API.

        Пример: self.call("messages.send", peer_id=1, message="привет").
        """
        data = {"access_token": self.token, "v": self.api_version, **params}
        response = self.session.post(f"{API_URL}/{method}", data=data, timeout=30)
        response.raise_for_status()  # сетевые ошибки 4xx/5xx → исключение requests
        payload = response.json()

        # ВК умеет отвечать HTTP 200 и класть ошибку внутрь JSON.
        # Без этой проверки метод молча вернул бы None.
        if "error" in payload:
            message = payload["error"].get("error_msg", "неизвестная ошибка ВК")
            raise RuntimeError(f"ВК: {message}")

        return payload.get("response")

    def send_message(self, peer_id: int, text: str, *, keyboard: str | None = None) -> None:
        """Отправляет сообщение в диалог.

        peer_id — идентификатор диалога. Для личных сообщений сообщества
        он совпадает с id пользователя.
        """
        params: dict[str, Any] = {
            "peer_id": peer_id,
            "message": text,
            # random_id обязателен: по нему ВК отличает новое сообщение от дубля.
            "random_id": secrets.randbits(63),
        }
        if keyboard:
            params["keyboard"] = keyboard
        self.call("messages.send", **params)

    def long_poll(self) -> Iterator[dict]:
        """Бесконечный поток событий сообщества.

        Как это работает:
        1. groups.getLongPollServer выдаёт адрес, ключ и номер события (ts).
        2. GET a_check ждёт до 25 секунд и возвращает новые события.
        3. ts из ответа передаём в следующий запрос — так ВК понимает,
           что мы уже прочитали.

        Сетевые ошибки не пробрасываются наружу: бот переподключается сам,
        иначе один таймаут `lp.vk.com` останавливал бы его до ручного запуска.
        """
        server, key, ts = self._long_poll_session()
        log.debug("LongPoll сессия: server=%s ts=%s key=%s…", server, ts, key[:6])
        failures = 0

        while True:
            try:
                response = self.session.get(
                    server,
                    params={"act": "a_check", "key": key, "ts": ts, "wait": LONG_POLL_WAIT},
                    timeout=LONG_POLL_WAIT + 15,
                )
                response.raise_for_status()
                data = response.json()
            except (requests.RequestException, ValueError) as exc:
                # Обрыв связи или мусор вместо JSON: ждём и повторяем с тем же ts.
                failures += 1
                log.warning(
                    "LongPoll: %s (%s/%s), повтор через %s с",
                    exc.__class__.__name__,
                    failures,
                    SESSION_RETRIES,
                    RETRY_DELAY,
                )
                time.sleep(RETRY_DELAY)
                if failures >= SESSION_RETRIES:
                    failures = 0
                    try:
                        server, key, ts = self._long_poll_session()
                        log.debug("Новая сессия: server=%s ts=%s", server, ts)
                    except (requests.RequestException, ValueError):
                        # ВК тоже недоступен — остаёмся на старой сессии и пробуем ещё.
                        log.warning("LongPoll: не удалось получить новую сессию", exc_info=True)
                continue

            failures = 0

            failed = data.get("failed")
            if failed == 1:
                # Небольшой разрыв, но можно продолжать с нового ts.
                log.debug("a_check: failed=1, новый ts=%s", data["ts"])
                ts = str(data["ts"])
                continue
            if failed in (2, 3):
                # Ключ устарел или история потеряна — берём сессию заново.
                log.warning("LongPoll: failed=%s, переподключаюсь", failed)
                server, key, ts = self._long_poll_session()
                log.debug("Новая сессия: server=%s ts=%s", server, ts)
                continue

            updates = data.get("updates", [])
            log.debug("a_check: ts=%s, новых событий: %s", data.get("ts"), len(updates))
            ts = str(data["ts"])
            for update in updates:
                # Сырое событие ВК — то, что реально пришло по сети.
                log.debug("update: %s", json.dumps(update, ensure_ascii=False))
                yield update

    def _long_poll_session(self) -> tuple[str, str, str]:
        """Получает server/key/ts для нового подключения."""
        info = self.call("groups.getLongPollServer", group_id=self.group_id)
        server = str(info["server"])
        # ВК иногда отдаёт адрес без схемы — requests требует http(s)://.
        if not server.startswith("http"):
            server = f"https://{server}"
        log.debug(
            "groups.getLongPollServer: server=%s ts=%s (key скрыт)",
            server,
            info["ts"],
        )
        return server, str(info["key"]), str(info["ts"])
