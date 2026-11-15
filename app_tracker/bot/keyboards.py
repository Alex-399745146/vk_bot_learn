"""Клавиатуры. ВК ждёт JSON-строку."""

from __future__ import annotations

import json

from .constants import CHILL_LIMIT

# ВК: до 40 кнопок, до 10 рядов по 5 для reply и до 6 рядов для inline.
# Подпись кнопки — не длиннее 40 символов.
BUTTON_LABEL_LIMIT = 40
MODERATORS_PAGE_SIZE = 5


def button(label: str, cmd: str, *, color: str = "secondary") -> dict:
    return {
        "action": {
            "type": "text",
            "label": label,
            "payload": json.dumps({"cmd": cmd}, ensure_ascii=False),
        },
        "color": color,
    }


def callback_button(label: str, cmd: str, *, color: str = "secondary") -> dict:
    """Inline-кнопка: нажатие не создаёт сообщение, приходит message_event."""
    return {
        "action": {
            "type": "callback",
            "label": label,
            "payload": json.dumps({"cmd": cmd}, ensure_ascii=False),
        },
        "color": color,
    }


def reply_keyboard(rows: list[list[dict]]) -> str:
    return json.dumps({"one_time": False, "buttons": rows}, ensure_ascii=False)


def inline_keyboard(rows: list[list[dict]]) -> str:
    return json.dumps({"inline": True, "buttons": rows}, ensure_ascii=False)


def empty_keyboard() -> str:
    """Явно убирает reply-клавиатуру, пока ждём текст."""
    return json.dumps({"buttons": []}, ensure_ascii=False)


def main_menu(
    *,
    can_checkin: bool = True,
    chill_left: int | None = None,
    is_superuser: bool = False,
) -> str:
    first_row: list[dict] = []
    if can_checkin:
        first_row.append(button("Отметиться", "menu:checkin", color="positive"))
    if chill_left:
        first_row.append(button(f"❄️ Chill {chill_left}/{CHILL_LIMIT}", "chill:start", color="primary"))

    rows: list[list[dict]] = []
    if first_row:
        rows.append(first_row)
    rows.append(
        [
            button("Мои цели", "menu:goals"),
            button("Изменить цели", "menu:edit"),
        ]
    )
    if is_superuser:
        rows.append([button("🛡 Модераторы", "mod:list")])
    return reply_keyboard(rows)


def moderators_list(participants, *, page: int, pages: int, owner_vk_id: int = 0) -> str:
    """Inline-список участников: 🟢 — модератор, ⚪ — обычный.

    Переключателя в ВК нет, поэтому ползунок эмулируем цветом кнопки
    (positive — зелёный, secondary — серый) и значком.
    """
    rows: list[list[dict]] = []
    for person in participants:
        name = f"{person.last_name} {person.first_name}".strip() or f"VK {person.vk_id}"
        if owner_vk_id and person.vk_id == owner_vk_id:
            label = f"👑 {name}"
            cmd = "mod:self"
            color = "primary"
        else:
            mark = "🟢" if person.is_moderator else "⚪"
            label = f"{mark} {name}"
            cmd = f"mod:toggle:{person.pk}"
            color = "positive" if person.is_moderator else "secondary"
        rows.append([callback_button(label[:BUTTON_LABEL_LIMIT], cmd, color=color)])

    nav: list[dict] = []
    if page > 1:
        nav.append(callback_button("‹ Назад", f"mod:page:{page - 1}"))
    nav.append(callback_button("✖ Закрыть", "mod:close"))
    if page < pages:
        nav.append(callback_button("Вперёд ›", f"mod:page:{page + 1}"))
    rows.append(nav)

    return inline_keyboard(rows)


def chill_warning() -> str:
    """Предупреждение перед использованием Chill."""
    return reply_keyboard(
        [
            [
                button("Передумал", "menu:cancel", color="positive"),
                button("Продолжить", "chill:ok", color="negative"),
            ]
        ]
    )


def goals_confirm() -> str:
    return reply_keyboard(
        [
            [
                button("Верно", "onb:ok", color="positive"),
                button("Изменить", "onb:edit"),
            ]
        ]
    )


def yes_no() -> str:
    return reply_keyboard(
        [
            [
                button("Да", "rep:yes", color="positive"),
                button("Нет", "rep:no"),
            ],
            [button("Отмена", "menu:cancel")],
        ]
    )


def report_exists() -> str:
    return reply_keyboard(
        [
            [
                button("Изменить", "rep:edit", color="primary"),
                button("Меню", "menu:cancel"),
            ]
        ]
    )
