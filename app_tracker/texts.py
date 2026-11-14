"""Тексты и форматирование сообщений.

Здесь нет ни базы, ни HTTP — только строки. Поэтому этот модуль
можно менять, не рискуя сломать логику.
"""

from __future__ import annotations

from app_tracker.constants import GOAL_COUNT

HELP_TEXT = (
    "Как пользоваться ботом:\n\n"
    "• Цели ставятся на месяц — три цели.\n"
    "• Каждый день жми «Отметиться» и отвечай «Да» или «Нет» по каждой цели.\n"
    "• Если выполнены все три — кнопка исчезает до следующих суток.\n"
    "• «Мои цели» — посмотреть цели, «Изменить цели» — поменять.\n\n"
    "Команды:\n"
    "/start — меню\n"
    "/help — инструкция"
)

MONTHS = (
    "январь",
    "февраль",
    "март",
    "апрель",
    "май",
    "июнь",
    "июль",
    "август",
    "сентябрь",
    "октябрь",
    "ноябрь",
    "декабрь",
)


def goals_text(goals: list[str], month_key: str = "") -> str:
    """Форматирует три цели для сообщения, с месяцем или без."""
    if month_key:
        lines = [f"Цели на {month_label(month_key)}:"]
    else:
        lines = ["Твои цели:"]
    for number, goal in enumerate(goals, start=1):
        lines.append(f"{number}. {goal}")
    return "\n".join(lines)


def report_text(participant, report, *, title: str) -> str:
    """Форматирует карточку отметки: статусы целей и итог дня."""
    marks = [report.goal_1_done, report.goal_2_done, report.goal_3_done]
    lines = [title]
    for number, goal in enumerate(participant.goals, start=1):
        mark = "✅" if marks[number - 1] else "❌"
        lines.append(f"{number}. {mark} {goal}")

    lines.append("")
    if report.completed:
        lines.append("День выполнен!")
    else:
        lines.append(f"Выполнено {report.goals_done} из {GOAL_COUNT}.")
    return "\n".join(lines)


def report_title(report, *, exists: bool) -> str:
    """Возвращает заголовок карточки: «Записал» или «Сегодня уже отмечено»."""
    if exists:
        return f"Сегодня уже отмечено: {report.goals_done} из {GOAL_COUNT}."
    return f"Записал: {report.goals_done} из {GOAL_COUNT}."


def month_label(month_key: str) -> str:
    """Преобразует YYYY-MM в «ноябрь 2026» для текста."""
    try:
        year, month = month_key.split("-")
        return f"{MONTHS[int(month) - 1]} {year}"
    except (ValueError, IndexError):
        return month_key
