"""Экраны: меню, справка и ответ на устаревшую кнопку."""

from __future__ import annotations

from . import keyboards
from .constants import CHILL_LIMIT, GOAL_COUNT
from .helpers import send
from app_tracker.models import BotState, Participant
from .storage import chill_count, reset_state, today_report
from .texts import HELP_TEXT, goals_text


def _menu_flags(
    participant: Participant, report
) -> tuple[bool, int, int]:
    """Возвращает (можно_отметиться, остаток Chill, использовано Chill)."""
    used = chill_count(participant)
    can_checkin = report is None or (not report.completed and not report.is_chill)
    can_chill = report is None and used < CHILL_LIMIT
    chill_left = CHILL_LIMIT - used if can_chill else 0
    return can_checkin, chill_left, used


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
    can_checkin, chill_left, chill_used = _menu_flags(participant, report)
    name = participant.first_name or "друг"
    text = (
        f"Привет, {name}!\n\n"
        f"{goals_text(participant.goals, participant.goals_month)}"
    )
    if report is not None:
        if report.is_chill:
            text += (
                f"\n\nСегодня Chill — отметка закрыта до завтра. "
                f"Chill за месяц: {chill_used} из {CHILL_LIMIT}."
            )
        elif report.completed:
            text += (
                "\n\nСегодня все три цели выполнены. "
                "Новая отметка будет доступна завтра."
            )
        else:
            text += (
                f"\n\nСегодня отмечено: {report.goals_done} из {GOAL_COUNT}. "
                "Можно дополнить — нажми «Отметиться»."
            )
    elif chill_left:
        text += f"\n\nChill: {chill_left} из {CHILL_LIMIT}."
    if intro:
        text = f"{intro}\n\n{text}"

    send(
        vk,
        peer_id,
        text,
        keyboards.main_menu(can_checkin=can_checkin, chill_left=chill_left),
    )


def menu_keyboard(participant: Participant) -> str:
    """Меню, учитывающее отметку за сегодня и остаток Chill."""
    report = today_report(participant)
    can_checkin, chill_left, _ = _menu_flags(participant, report)
    return keyboards.main_menu(can_checkin=can_checkin, chill_left=chill_left)


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
