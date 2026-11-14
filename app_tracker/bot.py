"""Тут мы работаем с сообщениями.

Меню, онбординг и ежедневная отметка.
Рецепт дня = три цели. День выполнен, если отмечены все три.

Состояния:
    IDLE → ONBOARD_GOAL → ONBOARD_CONFIRM → IDLE
    IDLE → REPORTING (три вопроса Да/Нет) → IDLE
"""

from __future__ import annotations

import json
import logging

from django.utils import timezone

from app_tracker import keyboards, states
from app_tracker.constants import GOAL_COUNT
from app_tracker.models import BotState, Participant, Report
from app_tracker.texts import (
    HELP_TEXT,
    goals_text,
    month_label,
    report_text,
    report_title,
)

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


# --- Текст -----------------------------------------------------------------


def handle_text(vk, participant: Participant, state: BotState, peer_id: int, text: str) -> None:
    """Обрабатывает текст отправляемый пользователем.

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
        if participant.has_goals:
            show_menu(vk, participant, state, peer_id)
        else:
            begin_onboarding(vk, participant, state, peer_id)
        return

    if state.state == states.ONBOARD_GOAL:
        add_goal(vk, participant, state, peer_id, text)
        return

    if state.state == states.ONBOARD_CONFIRM:
        send(vk, peer_id, "Нажми «Верно» или «Изменить».", keyboards.goals_confirm())
        return

    if state.state == states.REPORTING:
        send(vk, peer_id, "Ответь кнопкой «Да» или «Нет».", keyboards.yes_no())
        return

    if not participant.has_goals:
        begin_onboarding(vk, participant, state, peer_id)
    else:
        show_menu(vk, participant, state, peer_id, intro="Выбери действие кнопкой ниже.")


# --- Кнопки ----------------------------------------------------------------


def handle_command(
    vk, participant: Participant, state: BotState, peer_id: int, command: str
) -> None:
    """Обрабатывает нажатие кнопки: получает cmd и вызывает нужный шаг сценария."""
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
        if not participant.has_goals:
            begin_onboarding(vk, participant, state, peer_id)
            return
        report = today_report(participant)
        if report is not None and report.completed:
            send(
                vk,
                peer_id,
                report_text(participant, report, title=report_title(report, exists=True)),
                keyboards.report_exists(),
            )
            return
        start_report(vk, participant, state, peer_id)
        return

    if command == "menu:goals":
        if participant.has_goals:
            show_menu(vk, participant, state, peer_id)
        else:
            begin_onboarding(vk, participant, state, peer_id)
        return

    if command == "menu:edit":
        begin_onboarding(vk, participant, state, peer_id, edit=True)
        return

    if command == "menu:cancel":
        reset_state(state)
        if participant.has_goals:
            show_menu(vk, participant, state, peer_id)
        else:
            begin_onboarding(vk, participant, state, peer_id)
        return

    if command == "rep:edit":
        if participant.has_goals:
            start_report(vk, participant, state, peer_id)
        else:
            begin_onboarding(vk, participant, state, peer_id)
        return

    if command == "rep:yes":
        answer_report(vk, participant, state, peer_id, True)
        return

    if command == "rep:no":
        answer_report(vk, participant, state, peer_id, False)
        return

    send(vk, peer_id, "Не понял команду.", menu_keyboard(participant))


# --- Онбординг -------------------------------------------------------------


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


# --- Отметка ---------------------------------------------------------------


def start_report(vk, participant: Participant, state: BotState, peer_id: int) -> None:
    """Начинает отметку дня: обнуляет индекс и результаты, задаёт первый вопрос."""
    set_state(state, states.REPORTING, {"index": 0, "results": []})
    ask_goal(vk, participant, state, peer_id, 0)


def ask_goal(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    index: int,
) -> None:
    """Отправляет вопрос по цели с номером index и кнопки «Да»/«Нет»."""
    goal = participant.goals[index]
    send(
        vk,
        peer_id,
        f"Цель {index + 1} из {GOAL_COUNT}. {goal}\n\nВыполнено?",
        keyboards.yes_no(),
    )


def answer_report(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    done: bool,
) -> None:
    """Принимает ответ по цели; после третьего сохраняет Report и показывает итог."""
    if state.state != states.REPORTING:
        expired(vk, participant, peer_id)
        return

    data = dict(state.data or {})
    index = int(data.get("index", 0))
    results = list(data.get("results") or [])
    results.append(done)
    index += 1

    if index < GOAL_COUNT:
        set_state(state, states.REPORTING, {"index": index, "results": results})
        ask_goal(vk, participant, state, peer_id, index)
        return

    report, _ = Report.objects.update_or_create(
        participant=participant,
        date=timezone.localdate(),
        defaults={
            "goal_1_done": results[0],
            "goal_2_done": results[1],
            "goal_3_done": results[2],
        },
    )
    reset_state(state)
    send(
        vk,
        peer_id,
        report_text(participant, report, title=report_title(report, exists=False)),
        keyboards.main_menu(can_checkin=not report.completed),
    )


# --- Тексты ----------------------------------------------------------------








# --- Меню ------------------------------------------------------------------


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


def current_month() -> str:
    """Возвращает текущий месяц в формате YYYY-MM по часовому поясу проекта."""
    return timezone.localdate().strftime("%Y-%m")




# --- Служебное -------------------------------------------------------------


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


def validate_text(text: str) -> str | None:
    """Проверяет текст цели; возвращает текст ошибки или None, если всё в порядке."""
    if not text:
        return "Мне нужен текст."
    if text.startswith("/"):
        return "Напиши обычным текстом, без команд."
    if len(text) < 3:
        return "Слишком коротко, напиши ещё раз."
    return None


def expired(vk, participant: Participant, peer_id: int) -> None:
    """Отвечает на устаревшую кнопку и показывает актуальное меню."""
    send(vk, peer_id, "Это сообщение устарело.", menu_keyboard(participant))


def send(vk, peer_id: int, text: str, keyboard: str | None = None) -> None:
    """Отправляет сообщение через VK и пишет его в лог."""
    log.debug("Ответ в %s: %r", peer_id, text)
    vk.send_message(peer_id, text, keyboard=keyboard)


def fetch_user(vk, user_id: int) -> dict[str, str]:
    """Просит у ВК фамилию и имя: {'last_name': ..., 'first_name': ...}."""
    try:
        users = vk.call("users.get", user_ids=user_id)
    except Exception:
        log.warning("users.get не сработал", exc_info=True)
        return {"last_name": "", "first_name": "пользователь"}

    if users:
        user = users[0]
        return {
            "last_name": str(user.get("last_name") or ""),
            "first_name": str(user.get("first_name") or "пользователь"),
        }

    return {"last_name": "", "first_name": "пользователь"}
