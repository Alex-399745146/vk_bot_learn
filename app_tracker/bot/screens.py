"""Экраны: меню, справка и ответ на устаревшую кнопку."""

from __future__ import annotations

from . import keyboards
from .constants import GOAL_COUNT
from .helpers import send
from app_tracker.models import BotState, Participant
from .storage import reset_state, today_report
from .texts import HELP_TEXT, goals_text


def show_menu(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    *,
    intro: str | None = None,
) -> None:
    """Показывает цели и меню; если целей нет — запускает онбординг. Учитывает отметку за сегодня."""
    if not participant.has_goals:
        # Ленивый импорт: onboarding сам использует show_menu.
        from .onboarding import begin_onboarding

        begin_onboarding(vk, participant, state, peer_id)
        return

    reset_state(state)
    report = today_report(participant)
    name = participant.first_name or "друг"
    text = (
        f"Привет, {name}!\n\n"
        f"{goals_text(participant.goals, participant.goals_month)}"
    )
    if report is not None:
        if report.completed:
            text += (
                "\n\nСегодня все три цели выполнены. "
                "Новая отметка будет доступна завтра."
            )
        else:
            text += (
                f"\n\nСегодня отмечено: {report.goals_done} из {GOAL_COUNT}. "
                "Можно дополнить — нажми «Отметиться»."
            )
    if intro:
        text = f"{intro}\n\n{text}"

    can_checkin = report is None or not report.completed
    send(vk, peer_id, text, keyboards.main_menu(can_checkin=can_checkin))


def menu_keyboard(participant: Participant) -> str:
    """Меню без «Отметиться», только если все три цели выполнены."""
    report = today_report(participant)
    can_checkin = report is None or not report.completed
    return keyboards.main_menu(can_checkin=can_checkin)


def show_help(vk, participant: Participant, state: BotState, peer_id: int) -> None:
    """Показывает справку и подходящую клавиатуру: меню или приглашение начать."""
    reset_state(state)
    if participant.has_goals:
        send(vk, peer_id, HELP_TEXT, menu_keyboard(participant))
    else:
        send(
            vk,
            peer_id,
            f"{HELP_TEXT}\n\nЧтобы начать, напиши /start.",
            keyboards.empty_keyboard(),
        )


def expired(vk, participant: Participant, peer_id: int) -> None:
    """Отвечает на устаревшую кнопку и показывает актуальное меню."""
    send(vk, peer_id, "Это сообщение устарело.", menu_keyboard(participant))
