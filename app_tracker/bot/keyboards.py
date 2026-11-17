"""Reply-клавиатуры. ВК ждёт JSON-строку."""

from __future__ import annotations

import json

from .constants import CHILL_LIMIT, LIMIT_PAUSE


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


def main_menu(
    *,
    can_checkin: bool = True,
    chill_left: int | None = None,
    can_edit: bool = True,
    pause_left: int | None = None,
) -> str:
    """Три этажа: работа, окно целей, постоянные разделы.

    Chill показывается только вместе с «Отметиться», пауза — только
    вместе с «Изменить цели»: без первой кнопки вторая не имеет смысла.
    """
    rows: list[list[dict]] = []

    work_row: list[dict] = []
    if can_checkin:
        work_row.append(button("Отметиться", "menu:checkin", color="positive"))
        if chill_left:
            work_row.append(
                button(
                    f"❄️ Chill {chill_left}/{CHILL_LIMIT}",
                    "chill:start",
                    color="primary",
                )
            )
    if work_row:
        rows.append(work_row)

    window_row: list[dict] = []
    if can_edit:
        window_row.append(button("Изменить цели", "menu:edit", color="positive"))
        if pause_left:
            window_row.append(
                button(
                    f"⏸ Пауза {pause_left}/{LIMIT_PAUSE}",
                    "pause:start",
                    color="negative",
                )
            )
    if window_row:
        rows.append(window_row)

    rows.append(
        [
            button("Мои цели", "menu:goals"),
            button("Инструкция", "menu:help"),
        ]
    )
    return reply_keyboard(rows)


def chill_warning() -> str:
    """Предупреждение перед использованием Chill."""
    return reply_keyboard(
        [
            [
                button("Назад", "menu:cancel", color="positive"),
                button("Продолжить", "chill:ok", color="negative"),
            ]
        ]
    )


def pause_warning() -> str:
    """Предупреждение перед паузой."""
    return reply_keyboard(
        [
            [
                button("Назад", "pause:cancel", color="positive"),
                button("Продолжить", "pause:ok", color="negative"),
            ]
        ]
    )


def goals_confirm() -> str:
    return reply_keyboard(
        [
            [
                button("Верно", "onb:ok", color="positive"),
                button("Изменить", "onb:edit"),
            ],
            [button("Назад", "onb:back")],
        ]
    )


def goal_input(*, back: bool = True) -> str:
    """Ввод цели текстом: единственная кнопка — «Назад»."""
    if not back:
        return empty_keyboard()
    return reply_keyboard([[button("Назад", "onb:back")]])


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
