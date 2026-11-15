"""Мелкие помощники: отправка, проверки, дата, имя пользователя."""

from __future__ import annotations

import logging

from django.utils import timezone

log = logging.getLogger(__name__)


def send(vk, peer_id: int, text: str, keyboard: str | None = None) -> int | None:
    """Отправляет сообщение через VK, пишет его в лог и возвращает message_id."""
    log.debug("Ответ в %s: %r", peer_id, text)
    return vk.send_message(peer_id, text, keyboard=keyboard)


def validate_text(text: str) -> str | None:
    """Проверяет текст цели; возвращает текст ошибки или None, если всё в порядке."""
    if not text:
        return "Мне нужен текст."
    if text.startswith("/"):
        return "Напиши обычным текстом, без команд."
    if len(text) < 3:
        return "Слишком коротко, напиши ещё раз."
    return None


def current_month() -> str:
    """Возвращает текущий месяц в формате YYYY-MM по часовому поясу проекта."""
    return timezone.localdate().strftime("%Y-%m")


def fetch_user(vk, user_id: int) -> dict[str, str]:
    """Просит у ВК фамилию и имя: {'last_name': ..., 'first_name': ...}."""
    try:
        users = vk.call("users.get", user_ids=user_id)
    except Exception:
        log.warning("users.get не сработал", exc_info=True)
        return {"last_name": "", "first_name": "пользователь"}

    if users:
        user = users[0]
        return {
            "last_name": str(user.get("last_name") or ""),
            "first_name": str(user.get("first_name") or "пользователь"),
        }

    return {"last_name": "", "first_name": "пользователь"}
