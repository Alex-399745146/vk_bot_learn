"""Сборка reply-клавиатур.

ВК ждёт JSON-строку. Кнопка типа `text` приходит обратно как обычное
сообщение, но с полем `payload`.
"""

from __future__ import annotations

import json


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
    return json.dumps(
        {"one_time": False, "buttons": rows},
        ensure_ascii=False,
    )


def empty_keyboard() -> str:
    """Явно убирает reply-клавиатуру из чата."""
    return json.dumps({"buttons": []}, ensure_ascii=False)


def main_menu() -> str:
    return reply_keyboard(
        [
            [
                button("Мои правила", "menu:rules", color="primary"),
                button("Изменить правила", "menu:edit"),
            ]
        ]
    )


def confirm_keyboard() -> str:
    return reply_keyboard(
        [
            [
                button("Верно", "onb:ok", color="positive"),
                button("Изменить", "onb:edit"),
            ]
        ]
    )
