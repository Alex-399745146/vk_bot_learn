"""Обработчики сообщений: меню и онбординг.

Схема:
    первый текст → привычка → отказ → подтверждение → меню
    «Изменить правила» → заново привычка → отказ → подтверждение
"""

from __future__ import annotations

import json
import logging

from app_tracker import keyboards, states
from app_tracker.models import BotState, Participant

log = logging.getLogger(__name__)

START_WORDS = {"/start", "начать", "start", "меню", "menu"}


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
    normalized = text.casefold()

    # /start и «Меню» работают из любого состояния.
    if normalized in START_WORDS:
        if participant.habit:
            show_menu(vk, participant, state, peer_id)
        else:
            begin_onboarding(vk, participant, state, peer_id)
        return

    if state.state == states.ONBOARD_HABIT:
        error = validate_text(text)
        if error:
            send(vk, peer_id, error, keyboards.empty_keyboard())
            return

        data = dict(state.data or {})
        data["habit"] = text
        set_state(state, states.ONBOARD_REFUSAL, data)
        send(
            vk,
            peer_id,
            "Принял. Теперь напиши отказ — то, от чего отказываешься.",
            keyboards.empty_keyboard(),
        )
        return

    if state.state == states.ONBOARD_REFUSAL:
        error = validate_text(text)
        if error:
            send(vk, peer_id, error, keyboards.empty_keyboard())
            return

        data = dict(state.data or {})
        data["refusal"] = text
        set_state(state, states.ONBOARD_CONFIRM, data)
        send(vk, peer_id, confirm_text(data), keyboards.confirm_keyboard())
        return

    if state.state == states.ONBOARD_CONFIRM:
        send(
            vk,
            peer_id,
            "Нажми «Верно» или «Изменить».",
            keyboards.confirm_keyboard(),
        )
        return

    # IDLE: если правил ещё нет — знакомимся, иначе показываем меню.
    if not participant.habit:
        begin_onboarding(vk, participant, state, peer_id)
    else:
        show_menu(vk, participant, state, peer_id, intro="Выбери действие кнопкой ниже.")


# --- Кнопки ----------------------------------------------------------------


def handle_command(
    vk, participant: Participant, state: BotState, peer_id: int, command: str
) -> None:
    if command == "onb:ok":
        if state.state != states.ONBOARD_CONFIRM:
            send(vk, peer_id, "Это сообщение устарело.", keyboards.main_menu())
            return

        data = state.data or {}
        habit = str(data.get("habit") or "").strip()
        refusal = str(data.get("refusal") or "").strip()
        if not habit or not refusal:
            begin_onboarding(vk, participant, state, peer_id)
            return

        participant.habit = habit
        participant.refusal = refusal
        participant.save(update_fields=["habit", "refusal"])
        show_menu(vk, participant, state, peer_id, intro="Записал. Теперь я помню твои правила.")
        return

    if command == "onb:edit":
        if state.state != states.ONBOARD_CONFIRM:
            send(vk, peer_id, "Это сообщение устарело.", keyboards.main_menu())
            return
        begin_onboarding(vk, participant, state, peer_id, edit=True)
        return

    if command == "menu:rules":
        if participant.habit:
            show_menu(vk, participant, state, peer_id)
        else:
            begin_onboarding(vk, participant, state, peer_id)
        return

    if command == "menu:edit":
        begin_onboarding(vk, participant, state, peer_id, edit=True)
        return

    send(vk, peer_id, "Не понял команду.", keyboards.main_menu())


# --- Шаги ------------------------------------------------------------------


def begin_onboarding(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    *,
    edit: bool = False,
) -> None:
    set_state(state, states.ONBOARD_HABIT, {"habit": ""})
    name = participant.first_name or "друг"

    if edit:
        text = (
            f"{name}, давай обновим правила.\n\n"
            "Напиши новую привычку (например, «зарядка 10 минут»)."
        )
    else:
        text = (
            f"Привет, {name}! Я учебный бот.\n\n"
            "Давай запишем два правила на этот месяц.\n\n"
            "Напиши свою привычку (например, «зарядка 10 минут»)."
        )

    send(vk, peer_id, text, keyboards.empty_keyboard())


def show_menu(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    *,
    intro: str | None = None,
) -> None:
    reset_state(state)
    name = participant.first_name or "друг"
    text = (
        f"Привет, {name}!\n\n"
        f"Твои правила:\n"
        f"Привычка: {participant.habit}\n"
        f"Отказ: {participant.refusal}"
    )
    if intro:
        text = f"{intro}\n\n{text}"
    send(vk, peer_id, text, keyboards.main_menu())


def confirm_text(data: dict) -> str:
    return (
        "Проверь:\n"
        f"Привычка: {data.get('habit', '')}\n"
        f"Отказ: {data.get('refusal', '')}\n\n"
        "Всё верно?"
    )


# --- Служебное -------------------------------------------------------------


def get_participant(vk, vk_id: int) -> tuple[Participant, bool]:
    user = fetch_user(vk, vk_id)
    participant, created = Participant.objects.get_or_create(vk_id=vk_id, defaults=user)

    # Если запись уже была (например, после миграции), но имя пустое — заполним.
    if not created:
        changed: list[str] = []
        for field in ("last_name", "first_name"):
            if not getattr(participant, field) and user[field]:
                setattr(participant, field, user[field])
                changed.append(field)
        if changed:
            participant.save(update_fields=changed)

    return participant, created


def payload_command(message: dict) -> str | None:
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
    log.debug("Состояние %s -> %s", state.state, name)
    state.state = name
    state.data = data or {}
    state.save(update_fields=["state", "data", "updated_at"])


def reset_state(state: BotState) -> None:
    set_state(state, states.IDLE, {})


def validate_text(text: str) -> str | None:
    if not text:
        return "Мне нужен текст."
    if text.startswith("/"):
        return "Напиши обычным текстом, без команд."
    if len(text) < 3:
        return "Слишком коротко, напиши ещё раз."
    return None


def send(vk, peer_id: int, text: str, keyboard: str | None = None) -> None:
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
