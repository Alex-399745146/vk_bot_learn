"""Онбординг: ввод трёх целей на сезон."""

from __future__ import annotations

from django.utils import timezone

from . import keyboards, states
from .constants import GOAL_COUNT
from .helpers import send, validate_text
from app_tracker.models import BotState, GoalPeriod, Participant
from app_tracker.periods import (
    goals_window_label,
    is_goals_window,
    month_key,
    period_label,
    target_goals_month,
)
from .screens import expired, menu_keyboard, show_menu
from .storage import reset_state, set_state
from .texts import goals_text

PARTICIPATION_NOTE = (
    "Ставя цели, ты автоматически участвуешь в сезоне — так это "
    "расценивают организаторы."
)


def begin_onboarding(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    *,
    edit: bool = False,
) -> None:
    """Начинает или перезапускает ввод трёх целей и очищает черновик."""
    day = timezone.localdate()
    set_state(state, states.ONBOARD_GOAL, {"goals": [], "edit": edit})
    name = participant.first_name or "друг"
    period = period_label(target_goals_month(day))

    if edit:
        text = (
            f"{name}, давай обновим цели на период {period}.\n\n"
            "Цель 1 из 3. Напиши первую цель.\n"
            "Например: «активность >15 минут»."
        )
    else:
        text = (
            f"Привет, {name}! Я бот, я помогу тебе.\n\n"
            f"Давай поставим три цели на период {period}. "
            "Их нужно выполнять каждый день.\n"
            "Например: «активность 15 минут», «зарядка после сна», "
            "«без сахара в кофе».\n\n"
            "Цель 1 из 3. Напиши первую цель."
        )

    send(vk, peer_id, text, keyboards.goal_input(back=edit))


def add_goal(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    text: str,
) -> None:
    """Принимает очередную цель и после третьей показывает подтверждение."""
    data = dict(state.data or {})
    goals = list(data.get("goals") or [])
    edit = bool(data.get("edit"))

    error = validate_text(text)
    if error:
        send(vk, peer_id, error, keyboards.goal_input(back=edit or bool(goals)))
        return

    goals.append(text)

    if len(goals) < GOAL_COUNT:
        set_state(state, states.ONBOARD_GOAL, {"goals": goals, "edit": edit})
        send(
            vk,
            peer_id,
            f"Цель {len(goals) + 1} из {GOAL_COUNT}. Напиши следующую цель.",
            keyboards.goal_input(),
        )
        return

    set_state(state, states.ONBOARD_CONFIRM, {"goals": goals, "edit": edit})
    send(
        vk,
        peer_id,
        f"{goals_text(goals, target_goals_month(timezone.localdate()))}\n\n"
        f"{PARTICIPATION_NOTE}\n\nВсё верно?",
        keyboards.goals_confirm(),
    )


def go_back(vk, participant: Participant, state: BotState, peer_id: int) -> None:
    """Шаг назад: к предыдущей цели, а с первой — в меню без изменений."""
    data = dict(state.data or {})
    goals = list(data.get("goals") or [])
    edit = bool(data.get("edit"))

    if state.state == states.ONBOARD_CONFIRM:
        goals = goals[:-1]
        set_state(state, states.ONBOARD_GOAL, {"goals": goals, "edit": edit})
        send(
            vk,
            peer_id,
            f"Цель {len(goals) + 1} из {GOAL_COUNT}. Напиши её заново.",
            keyboards.goal_input(),
        )
        return

    if state.state != states.ONBOARD_GOAL:
        expired(vk, participant, peer_id)
        return

    if goals:
        goals.pop()
        set_state(state, states.ONBOARD_GOAL, {"goals": goals, "edit": edit})
        send(
            vk,
            peer_id,
            f"Цель {len(goals) + 1} из {GOAL_COUNT}. Напиши её заново.",
            keyboards.goal_input(back=edit or bool(goals)),
        )
        return

    reset_state(state)
    show_menu(vk, participant, state, peer_id, intro="Цели не изменены.")


def confirm_goals(vk, participant: Participant, state: BotState, peer_id: int) -> None:
    """Сохраняет три цели на целевой сезон и показывает меню."""
    if state.state != states.ONBOARD_CONFIRM:
        expired(vk, participant, peer_id)
        return

    day = timezone.localdate()
    if not is_goals_window(day):
        reset_state(state)
        send(
            vk,
            peer_id,
            "Окно целей закрыто: поставить или изменить цели можно "
            f"с {goals_window_label()} числа.",
            menu_keyboard(participant),
        )
        return

    goals = list((state.data or {}).get("goals") or [])
    if len(goals) != GOAL_COUNT or not all(goals):
        edit = bool((state.data or {}).get("edit"))
        begin_onboarding(vk, participant, state, peer_id, edit=edit)
        return

    month = target_goals_month(day)
    GoalPeriod.objects.update_or_create(
        participant=participant,
        month=month,
        defaults={
            "goal_1": goals[0],
            "goal_2": goals[1],
            "goal_3": goals[2],
            "status": "active",
        },
    )

    if month == month_key(day):
        participant.goal_1, participant.goal_2, participant.goal_3 = goals
        participant.goals_month = month
        participant.save(update_fields=["goal_1", "goal_2", "goal_3", "goals_month"])

    reset_state(state)

    if month == month_key(day):
        intro = "Записал. Цели на текущий период сохранены."
    else:
        intro = (
            f"Записал. Цели на период {period_label(month)} сохранены — "
            "сезон начнётся 3-го."
        )

    show_menu(vk, participant, state, peer_id, intro=intro)
