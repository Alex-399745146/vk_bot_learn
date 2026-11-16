"""Работа с базой и состоянием диалога.

Сценарии не ходят в ORM напрямую — они вызывают функции отсюда.
"""

from __future__ import annotations

import json
import logging
from datetime import date

from django.utils import timezone

from . import states
from .helpers import fetch_user
from app_tracker.models import BotState, Participant, Report

log = logging.getLogger(__name__)


def get_participant(vk, vk_id: int) -> tuple[Participant, bool]:
    """Находит участника по vk_id или создаёт его; обновляет имя, фото и пол."""
    user = fetch_user(vk, vk_id)
    defaults = {"last_name": user["last_name"], "first_name": user["first_name"]}
    participant, created = Participant.objects.get_or_create(vk_id=vk_id, defaults=defaults)

    if not created:
        changed: list[str] = []
        for field in ("last_name", "first_name"):
            if not getattr(participant, field) and user[field]:
                setattr(participant, field, user[field])
                changed.append(field)
        if changed:
            participant.save(update_fields=changed)

    update_participant_profile(participant, user)
    return participant, created


def today_report(participant: Participant) -> Report | None:
    """Возвращает отметку за сегодня или None."""
    return Report.objects.filter(
        participant=participant, date=timezone.localdate()
    ).first()


def chill_count(participant: Participant, day=None) -> int:
    """Сколько Chill уже использовано в месяце дня (по умолчанию — сегодня)."""
    day = day or timezone.localdate()
    return Report.objects.filter(
        participant=participant,
        date__year=day.year,
        date__month=day.month,
        is_chill=True,
    ).count()


def month_points(participant: Participant, day=None) -> int:
    """Баллы за месяц: по 1 за каждый день, где выполнены все три цели."""
    day = day or timezone.localdate()
    return Report.objects.filter(
        participant=participant,
        date__year=day.year,
        date__month=day.month,
        is_chill=False,
        goal_1_done=True,
        goal_2_done=True,
        goal_3_done=True,
    ).count()


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


def update_participant_profile(participant, vk_data: dict) -> None:
    """Обновляет фото и пол из ответа ВК; пишет в базу только изменения."""
    if not vk_data:
        return

    changed: list[str] = []

    photo_id = str(vk_data.get("photo_id") or "")
    if participant.photo_id != photo_id:
        participant.photo_id = photo_id
        changed.append("photo_id")

    try:
        sex = int(vk_data.get("sex") or 0)
    except (TypeError, ValueError):
        sex = 0
    if participant.sex != sex:
        participant.sex = sex
        changed.append("sex")

    # photo_200 приходит из ВК, photo_url — из нормализованного fetch_user.
    photo_url = str(vk_data.get("photo_url") or vk_data.get("photo_200") or "")
    if photo_url and participant.photo_url != photo_url:
        participant.photo_url = photo_url
        changed.append("photo_url")

    if changed:
        participant.save(update_fields=changed)


def create_chill_report(participant: Participant, day: date | None = None) -> Report:
    """Создает отчет со статусом Chill на сегодня."""
    day = day or timezone.localdate()
    report, created = Report.objects.get_or_create(
        participant=participant,
        date=day,
        defaults={'is_chill': True}
    )
    if not created:
        report.is_chill = True
        report.save(update_fields=['is_chill'])
    return report
