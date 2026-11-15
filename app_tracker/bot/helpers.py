"""Мелкие помощники: отправка, проверки, дата, имя пользователя."""

from __future__ import annotations

import logging

from django.utils import timezone

log = logging.getLogger(__name__)


def send(vk, peer_id: int, text: str, keyboard: str | None = None) -> None:
    """Отправляет сообщение через VK и пишет его в лог."""
    log.debug("Ответ в %s: %r", peer_id, text)
    vk.send_message(peer_id, text, keyboard=keyboard)


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


def fetch_user(vk, user_id: int) -> dict:
    """Просит у ВК имя, фамилию, фото и пол.

    Возвращает словарь с ключами `last_name`, `first_name`, `photo_id`,
    `photo_url`, `sex`. Если ВК не ответил — пустые значения, а имя
    «пользователь», чтобы сценарий не падал.
    """
    try:
        profile = vk.get_user_info(user_id) or {}
    except Exception:
        log.warning("users.get не сработал", exc_info=True)
        profile = {}

    try:
        sex = int(profile.get("sex") or 0)
    except (TypeError, ValueError):
        sex = 0

    return {
        "last_name": str(profile.get("last_name") or ""),
        "first_name": str(profile.get("first_name") or "пользователь"),
        "photo_id": str(profile.get("photo_id") or ""),
        "photo_url": str(profile.get("photo_200") or ""),
        "sex": sex,
    }
