"""Работа с базой и состоянием диалога.

Сценарии не ходят в ORM напрямую — они вызывают функции отсюда.
"""

from __future__ import annotations

import json
import logging

from django.utils import timezone

from app_tracker import states
from app_tracker.helpers import fetch_user
from app_tracker.models import BotState, Participant, Report

log = logging.getLogger(__name__)


def get_participant(vk, vk_id: int) -> tuple[Participant, bool]:
    """Находит участника по vk_id или создаёт его; заполняет пустые имя и фамилию."""
    user = fetch_user(vk, vk_id)
    participant, created = Participant.objects.get_or_create(vk_id=vk_id, defaults=user)

    if not created:
        changed: list[str] = []
        for field in ("last_name", "first_name"):
            if not getattr(participant, field) and user[field]:
                setattr(participant, field, user[field])
                changed.append(field)
        if changed:
            participant.save(update_fields=changed)

    return participant, created


def today_report(participant: Participant) -> Report | None:
    """Возвращает отметку за сегодня или None."""
    return Report.objects.filter(
        participant=participant, date=timezone.localdate()
    ).first()


def payload_command(message: dict) -> str | None:
    """Достаёт cmd из payload кнопки; возвращает None, если payload нет или он битый."""
    raw = message.get("payload")
    if not raw:
        return None

    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return None

    command = data.get("cmd") if isinstance(data, dict) else None
    return command if isinstance(command, str) else None


def set_state(state: BotState, name: str, data: dict | None = None) -> None:
    """Записывает состояние и данные шага в BotState."""
    log.debug("Состояние %s -> %s", state.state, name)
    state.state = name
    state.data = data or {}
    state.save(update_fields=["state", "data", "updated_at"])


def reset_state(state: BotState) -> None:
    """Сбрасывает состояние в IDLE и очищает данные шага."""
    set_state(state, states.IDLE, {})
