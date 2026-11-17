"""Работа с базой и состоянием диалога.

Сценарии не ходят в ORM напрямую — они вызывают функции отсюда.
"""

from __future__ import annotations

import json
import logging

from django.utils import timezone

from . import states
from .constants import LIMIT_PAUSE
from .helpers import fetch_user
from app_tracker.models import BotState, GoalPeriod, Participant, Report
from app_tracker.periods import target_goals_month, work_bounds, work_month

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
    sync_period_goals(participant)
    return participant, created


def sync_period_goals(participant: Participant, day=None) -> GoalPeriod | None:
    """Переносит цели периода в активные поля участника в рабочий период."""
    day = day or timezone.localdate()
    month = work_month(day)
    if month is None:
        return None

    period = GoalPeriod.objects.filter(participant=participant, month=month).first()
    if period is None:
        return None

    if period.status == "paused":
        if participant.goals_month or any(participant.goals):
            participant.goal_1 = participant.goal_2 = participant.goal_3 = ""
            participant.goals_month = ""
            participant.save(update_fields=["goal_1", "goal_2", "goal_3", "goals_month"])
        return period

    if participant.goals_month != month or participant.goals != period.goals:
        participant.goal_1, participant.goal_2, participant.goal_3 = period.goals
        participant.goals_month = month
        participant.save(update_fields=["goal_1", "goal_2", "goal_3", "goals_month"])

    return period


def pause_count(participant: Participant, year: int | None = None) -> int:
    """Сколько пауз взято за календарный год."""
    year = year or timezone.localdate().year
    return GoalPeriod.objects.filter(
        participant=participant, status="paused", paused_at__year=year
    ).count()


def pause_left(participant: Participant, day=None) -> int:
    """Сколько пауз осталось в этом календарном году."""
    day = day or timezone.localdate()
    return max(0, LIMIT_PAUSE - pause_count(participant, day.year))


def target_paused(participant: Participant, day=None) -> bool:
    """Выбрана ли пауза на период, который ставится в текущем окне."""
    day = day or timezone.localdate()
    target = target_goals_month(day)
    return GoalPeriod.objects.filter(
        participant=participant, month=target, status="paused"
    ).exists()


def today_report(participant: Participant) -> Report | None:
    """Возвращает отметку за сегодня или None."""
    return Report.objects.filter(
        participant=participant, date=timezone.localdate()
    ).first()


def chill_count(participant: Participant, day=None) -> int:
    """Сколько Chill использовано в текущем рабочем периоде (3–28)."""
    day = day or timezone.localdate()
    month = work_month(day)
    if month is None:
        return 0

    start, end = work_bounds(month)
    return Report.objects.filter(
        participant=participant,
        date__range=(start, end),
        is_chill=True,
    ).count()


def period_points(participant: Participant, day=None) -> int:
    """Баллы периода: по 1 за каждый день 3–28, где выполнены все три цели."""
    day = day or timezone.localdate()
    month = work_month(day) or participant.goals_month
    if not month:
        return 0

    if GoalPeriod.objects.filter(
        participant=participant, month=month, status="paused"
    ).exists():
        return 0

    start, end = work_bounds(month)
    return Report.objects.filter(
        participant=participant,
        date__range=(start, end),
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
