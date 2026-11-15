"""Онбординг: ввод трёх целей на текущий месяц."""

from __future__ import annotations

from . import keyboards, states
from .constants import GOAL_COUNT
from .helpers import current_month, send, validate_text
from app_tracker.models import BotState, Participant
from .screens import expired, show_menu
from .storage import reset_state, set_state
from .texts import goals_text, month_label


def begin_onboarding(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    *,
    edit: bool = False,
) -> None:
    """Начинает или перезапускает ввод трёх целей и очищает черновик."""
    set_state(state, states.ONBOARD_GOAL, {"goals": [], "edit": edit})
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

    send(vk, peer_id, text, keyboards.goal_input(back=edit))


def add_goal(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    text: str,
) -> None:
    """Принимает очередную цель, складывает её в BotState.data и после третьей показывает подтверждение."""
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
        f"{goals_text(goals, current_month())}\n\nВсё верно?",
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

    # Черновик пуст: в режиме редактирования выходим в меню, старые цели целы.
    if edit and participant.has_goals:
        reset_state(state)
        show_menu(vk, participant, state, peer_id, intro="Цели не изменены.")
        return

    send(
        vk,
        peer_id,
        "Это первый шаг — напиши первую цель.",
        keyboards.goal_input(back=False),
    )


def confirm_goals(vk, participant: Participant, state: BotState, peer_id: int) -> None:
    """Сохраняет три цели в Participant, ставит текущий месяц и показывает меню."""
    if state.state != states.ONBOARD_CONFIRM:
        expired(vk, participant, peer_id)
        return

    goals = list((state.data or {}).get("goals") or [])
    if len(goals) != GOAL_COUNT or not all(goals):
        edit = bool((state.data or {}).get("edit"))
        begin_onboarding(vk, participant, state, peer_id, edit=edit)
        return

    participant.goal_1, participant.goal_2, participant.goal_3 = goals
    participant.goals_month = current_month()
    participant.save(update_fields=["goal_1", "goal_2", "goal_3", "goals_month"])
    show_menu(vk, participant, state, peer_id, intro="Записал. Цели на месяц сохранены.")
