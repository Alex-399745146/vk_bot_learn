"""Маршрутизация сообщений бота.

Сюда приходит событие из runbot.py. Модуль не содержит сценариев:
он только решает, какой обработчик вызвать.

Сценарии лежат рядом:
    onboarding.py — ввод трёх целей;
    reporting.py  — ежедневная отметка;
    screens.py    — меню и справка.
"""

from __future__ import annotations

import logging

from django.utils import timezone

from . import keyboards, states
from .helpers import send
from app_tracker.models import BotState, Participant
from app_tracker.periods import goals_window_label, is_goals_window, is_work_period
from .onboarding import add_goal, begin_onboarding, confirm_goals, go_back
from .reporting import answer_report, confirm_chill, handle_checkin, handle_chill, start_report
from .screens import expired, menu_keyboard, no_goals_hint, show_help, show_menu
from .storage import get_participant, payload_command, reset_state

log = logging.getLogger(__name__)

START_WORDS = {"/start", "начать", "start", "меню", "menu"}
HELP_WORDS = {"/help", "помощь", "help", "инструкция"}


def handle_update(vk, update: dict) -> None:
    """Обрабатывает одно событие LongPoll."""
    event_type = update.get("type")
    log.debug("Событие: %s", event_type)

    if event_type != "message_new":
        return

    message = update["object"]["message"]

    # Сообщения самого сообщества (from_id < 0) не обрабатываем.
    if message["from_id"] <= 0:
        return

    text = (message.get("text") or "").strip()
    vk_id = message["from_id"]
    peer_id = message["peer_id"]

    participant, _ = get_participant(vk, vk_id)
    state, _ = BotState.objects.get_or_create(vk_id=vk_id)
    command = payload_command(message)

    log.debug(
        "Сообщение от %s: state=%s cmd=%s text=%r",
        vk_id,
        state.state,
        command,
        text,
    )

    if command:
        handle_command(vk, participant, state, peer_id, command)
    else:
        handle_text(vk, participant, state, peer_id, text)


def handle_text(vk, participant: Participant, state: BotState, peer_id: int, text: str) -> None:
    """Обрабатывает текстовое сообщение пользователя.

    Порядок важен — проверки идут сверху вниз:

    1. Справка: /help и «помощь» показывают инструкцию.
    2. Старт: /start и «меню» показывают меню или запускают онбординг.
    3. Текущее состояние:
       - ONBOARD_GOAL — текст считается очередной целью;
       - ONBOARD_CONFIRM — напоминаем нажать «Верно» или «Изменить»;
       - REPORTING — напоминаем ответить «Да» или «Нет».
    4. Всё остальное:
       - целей нет — начинаем онбординг;
       - цели есть — показываем меню с подсказкой.

    Нажатия кнопок сюда не попадают: их разбирает handle_command()
    по полю payload.
    """
    normalized = text.casefold()

    if normalized in HELP_WORDS:
        show_help(vk, participant, state, peer_id)
        return

    if normalized in START_WORDS:
        show_menu(vk, participant, state, peer_id)
        return

    if state.state == states.ONBOARD_GOAL:
        add_goal(vk, participant, state, peer_id, text)
        return

    if state.state == states.ONBOARD_CONFIRM:
        send(
            vk,
            peer_id,
            "Нажми «Верно», «Изменить» или «Назад».",
            keyboards.goals_confirm(),
        )
        return

    if state.state == states.REPORTING:
        send(vk, peer_id, "Ответь кнопкой «Да» или «Нет».", keyboards.yes_no())
        return

    if state.state == states.CHILL_CONFIRM:
        send(
            vk,
            peer_id,
            "Нажми «Передумал» или «Продолжить».",
            keyboards.chill_warning(),
        )
        return

    show_menu(vk, participant, state, peer_id, intro="Выбери действие кнопкой ниже.")


def handle_command(
    vk, participant: Participant, state: BotState, peer_id: int, command: str
) -> None:
    """Обрабатывает нажатие кнопки: получает cmd и вызывает нужный шаг сценария."""
    if command == "onb:back":
        go_back(vk, participant, state, peer_id)
        return

    if command == "onb:ok":
        confirm_goals(vk, participant, state, peer_id)
        return

    if command == "onb:edit":
        if state.state != states.ONBOARD_CONFIRM:
            expired(vk, participant, peer_id)
            return
        begin_onboarding(vk, participant, state, peer_id, edit=True)
        return

    if command == "menu:checkin":
        handle_checkin(vk, participant, state, peer_id)
        return

    if command == "chill:start":
        handle_chill(vk, participant, state, peer_id)
        return

    if command == "chill:ok":
        confirm_chill(vk, participant, state, peer_id)
        return

    if command == "menu:goals":
        show_menu(vk, participant, state, peer_id)
        return

    if command == "menu:edit":
        if not is_goals_window(timezone.localdate()):
            send(
                vk,
                peer_id,
                "Окно целей закрыто. Поставить или изменить цели можно "
                f"с {goals_window_label()} числа.",
                menu_keyboard(participant),
            )
            return
        begin_onboarding(vk, participant, state, peer_id, edit=True)
        return

    if command == "menu:help":
        show_help(vk, participant, state, peer_id)
        return

    if command == "menu:cancel":
        reset_state(state)
        show_menu(vk, participant, state, peer_id)
        return

    if command == "rep:edit":
        if is_work_period(timezone.localdate()) and participant.has_goals:
            start_report(vk, participant, state, peer_id)
        else:
            send(vk, peer_id, no_goals_hint(participant), menu_keyboard(participant))
        return

    if command == "rep:yes":
        answer_report(vk, participant, state, peer_id, True)
        return

    if command == "rep:no":
        answer_report(vk, participant, state, peer_id, False)
        return

    send(vk, peer_id, "Не понял команду.", menu_keyboard(participant))
