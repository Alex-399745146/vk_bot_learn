"""Пауза: пропуск следующего периода, до 3 раз за календарный год."""

from __future__ import annotations

import logging

from django.utils import timezone

from app_tracker.models import BotState, GoalPeriod, Participant
from app_tracker.periods import (
    goals_window_label,
    is_goals_window,
    month_key,
    period_label,
    target_goals_month,
)

from . import keyboards, states
from .constants import LIMIT_PAUSE
from .helpers import send
from .screens import expired, menu_keyboard, show_menu
from .storage import pause_left, reset_state, set_state

log = logging.getLogger(__name__)


def handle_pause(vk, participant: Participant, state: BotState, peer_id: int) -> None:
    """Проверяет окно и лимит, показывает предупреждение."""
    day = timezone.localdate()

    if not is_goals_window(day):
        send(
            vk,
            peer_id,
            "Паузу можно взять только в окне целей: "
            f"с {goals_window_label()} число.",
            menu_keyboard(participant),
        )
        return

    if state.state == states.PAUSE_CONFIRM:
        send(vk, peer_id, "Нажми «Назад» или «Продолжить».", keyboards.pause_warning())
        return

    if state.state != states.IDLE:
        expired(vk, participant, peer_id)
        return

    left = pause_left(participant, day)
    if left <= 0:
        send(
            vk,
            peer_id,
            f"Лимит пауз исчерпан: {LIMIT_PAUSE} из {LIMIT_PAUSE} за этот год.",
            menu_keyboard(participant),
        )
        return

    target = target_goals_month(day)
    existing = GoalPeriod.objects.filter(
        participant=participant, month=target
    ).first()
    if existing is not None and existing.status == "paused":
        send(
            vk,
            peer_id,
            f"Пауза на период {period_label(target)} уже выбрана.",
            menu_keyboard(participant),
        )
        return

    used = LIMIT_PAUSE - left
    set_state(state, states.PAUSE_CONFIRM, {"target": target})
    send(
        vk,
        peer_id,
        f"Паузу можно использовать {LIMIT_PAUSE} раза в году. "
        f"Сейчас будет {used + 1}-й из {LIMIT_PAUSE}.\n\nПродолжить?",
        keyboards.pause_warning(),
    )


def confirm_pause(vk, participant: Participant, state: BotState, peer_id: int) -> None:
    """Записывает паузу: целевой период закрывается с 0 баллов."""
    if state.state != states.PAUSE_CONFIRM:
        expired(vk, participant, peer_id)
        return

    day = timezone.localdate()
    if not is_goals_window(day):
        reset_state(state)
        send(
            vk,
            peer_id,
            "Окно целей уже закрыто — пауза недоступна.",
            menu_keyboard(participant),
        )
        return

    if pause_left(participant, day) <= 0:
        reset_state(state)
        send(
            vk,
            peer_id,
            f"Лимит пауз исчерпан: {LIMIT_PAUSE} из {LIMIT_PAUSE} за этот год.",
            menu_keyboard(participant),
        )
        return

    target = target_goals_month(day)
    existing = GoalPeriod.objects.filter(
        participant=participant, month=target
    ).first()
    if existing is not None and existing.status == "paused":
        reset_state(state)
        send(
            vk,
            peer_id,
            f"Пауза на период {period_label(target)} уже выбрана.",
            menu_keyboard(participant),
        )
        return

    GoalPeriod.objects.update_or_create(
        participant=participant,
        month=target,
        defaults={
            "status": "paused",
            "paused_at": timezone.now(),
            "goal_1": "",
            "goal_2": "",
            "goal_3": "",
        },
    )

    if target == month_key(day):
        participant.goal_1 = participant.goal_2 = participant.goal_3 = ""
        participant.goals_month = ""
        participant.save(update_fields=["goal_1", "goal_2", "goal_3", "goals_month"])

    reset_state(state)
    left = pause_left(participant, day)
    send(
        vk,
        peer_id,
        (
            f"Пауза записана: период {period_label(target)} пропущен, "
            f"баллы за него — 0.\n"
            f"Осталось пауз в этом году: {left} из {LIMIT_PAUSE}."
        ),
        menu_keyboard(participant),
    )


def cancel_pause(vk, participant: Participant, state: BotState, peer_id: int) -> None:
    """Отмена паузы: возврат в меню без изменений."""
    reset_state(state)
    show_menu(vk, participant, state, peer_id, intro="Пауза не взята.")
