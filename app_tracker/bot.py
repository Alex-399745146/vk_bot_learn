"""Обработчики сообщений. Здесь появляется работа с базой."""

from __future__ import annotations

import logging

from app_tracker.models import Participant

log = logging.getLogger(__name__)


def handle_update(vk, update: dict) -> None:
    """Обрабатывает одно событие LongPoll."""
    event_type = update.get("type")
    log.debug("Событие: %s", event_type)

    if event_type != "message_new":
        return

    message = update["object"]["message"]

    # Сообщения самого сообщества (from_id < 0) не обрабатываем.
    # Что-бы бот сам себе не отвечал.
    if message["from_id"] <= 0:
        return

    text = (message.get("text") or "").strip()
    vk_id = message["from_id"]
    peer_id = message["peer_id"]

    log.debug("Сообщение от %s: %r", vk_id, text)

    name = fetch_name(vk, vk_id)

    # get_or_create: ищем участника по vk_id, а если его нет — создаём.
    participant, created = Participant.objects.get_or_create(
        vk_id=vk_id,
        defaults={"name": name},
    )

    if created:
        reply = (
            f"Привет, {name}! Я добавил тебя в базу учёта нашей группы.\n"
            "Теперь мы тебя запомнили."
        )
    else:
        reply = (
            f"С возвращением, {participant.name}! "
            f"Ты в базе с {participant.created_at:%d.%m.%Y}."
        )

    log.debug("Ответ в %s: %r", peer_id, reply)
    vk.send_message(peer_id, reply)


def fetch_name(vk, user_id: int) -> str:
    """Просит у ВК имя пользователя. Если не вышло — возвращает «пользователь»."""
    try:
        users = vk.call("users.get", user_ids=user_id, fields="first_name")
    except Exception:
        log.warning("users.get не сработал", exc_info=True)
        return "пользователь"

    if users:
        return str(users[0].get("first_name") or "пользователь")
    return "пользователь"
