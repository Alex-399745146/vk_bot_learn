"""Онбординг: ввод трёх целей на текущий месяц."""

from __future__ import annotations

from app_tracker import keyboards, states
from app_tracker.constants import GOAL_COUNT
from app_tracker.helpers import current_month, send, validate_text
from app_tracker.models import BotState, Participant
from app_tracker.screens import expired, show_menu
from app_tracker.storage import set_state
from app_tracker.texts import goals_text, month_label


def begin_onboarding(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    *,
    edit: bool = False,
) -> None:
    """Начинает или перезапускает ввод трёх целей и очищает черновик."""
    set_state(state, states.ONBOARD_GOAL, {"goals": []})
    name = participant.first_name or "друг"
    month = month_label(current_month())

    if edit:
        text = (
            f"{name}, давай обновим цели на {month}.\n\n"
            "Цель 1 из 3. Напиши первую цель.\n"
            "Например: «активность >15 минут»."
        )
    else:
        text = (
            f"Привет, {name}! Я бот, я помогу тебе.\n\n"
            f"Давай поставим три цели на {month}. Их нужно выполнять каждый день.\n"
            "Например: «активность 15 минут», «зарядка после сна», "
            "«без сахара в кофе».\n\n"
            "Цель 1 из 3. Напиши первую цель."
        )

    send(vk, peer_id, text, keyboards.empty_keyboard())


def add_goal(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    text: str,
) -> None:
    """Принимает очередную цель, складывает её в BotState.data и после третьей показывает подтверждение."""
    error = validate_text(text)
    if error:
        send(vk, peer_id, error, keyboards.empty_keyboard())
        return

    data = dict(state.data or {})
    goals = list(data.get("goals") or [])
    goals.append(text)

    if len(goals) < GOAL_COUNT:
        set_state(state, states.ONBOARD_GOAL, {"goals": goals})
        send(
            vk,
            peer_id,
            f"Цель {len(goals) + 1} из {GOAL_COUNT}. Напиши следующую цель.",
            keyboards.empty_keyboard(),
        )
        return

    set_state(state, states.ONBOARD_CONFIRM, {"goals": goals})
    send(
        vk,
        peer_id,
        f"{goals_text(goals, current_month())}\n\nВсё верно?",
        keyboards.goals_confirm(),
    )


def confirm_goals(vk, participant: Participant, state: BotState, peer_id: int) -> None:
    """Сохраняет три цели в Participant, ставит текущий месяц и показывает меню."""
    if state.state != states.ONBOARD_CONFIRM:
        expired(vk, participant, peer_id)
        return

    goals = list((state.data or {}).get("goals") or [])
    if len(goals) != GOAL_COUNT or not all(goals):
        begin_onboarding(vk, participant, state, peer_id)
        return

    participant.goal_1, participant.goal_2, participant.goal_3 = goals
    participant.goals_month = current_month()
    participant.save(update_fields=["goal_1", "goal_2", "goal_3", "goals_month"])
    show_menu(vk, participant, state, peer_id, intro="Записал. Цели на месяц сохранены.")
