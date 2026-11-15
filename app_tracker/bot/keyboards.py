"""Reply-клавиатуры. ВК ждёт JSON-строку."""

from __future__ import annotations

import json

from .constants import CHILL_LIMIT


def button(label: str, cmd: str, *, color: str = "secondary") -> dict:
    return {
        "action": {
            "type": "text",
            "label": label,
            "payload": json.dumps({"cmd": cmd}, ensure_ascii=False),
        },
        "color": color,
    }


def reply_keyboard(rows: list[list[dict]]) -> str:
    return json.dumps({"one_time": False, "buttons": rows}, ensure_ascii=False)


def empty_keyboard() -> str:
    """Явно убирает reply-клавиатуру, пока ждём текст."""
    return json.dumps({"buttons": []}, ensure_ascii=False)


def main_menu(*, can_checkin: bool = True, chill_left: int | None = None) -> str:
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
    return reply_keyboard(rows)


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
