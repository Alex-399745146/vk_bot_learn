"""Тексты и форматирование сообщений.

Здесь нет ни базы, ни HTTP — только строки. Поэтому этот модуль
можно менять, не рискуя сломать логику.
"""

from __future__ import annotations

from .constants import GOAL_COUNT

HELP_TEXT = (
    "🔥 ГОРЯЧИЙ РАЗГОН · как всё устроено\n"
    "──────────────\n"
    "🎯 ЦЕЛИ\n"
    "На месяц — три цели. Их нужно выполнять каждый день.\n"
    "«Изменить цели» — переписать их в любой момент.\n\n"
    "✅ ОТМЕТКА ДНЯ\n"
    "Жми «Отметиться» и отвечай «Да» или «Нет» по каждой цели.\n"
    "• 3 из 3 — 1 балл в копилку месяца;\n"
    "• 1–2 из 3 — баллов нет, но день можно дополнить до конца суток.\n\n"
    "❄️ CHILL\n"
    "До 3 раз в месяц — день отдыха: 0 баллов, день закрыт.\n"
    "С обычной отметкой не сочетается: один день — один статус.\n"
    "После Chill «Отметиться» вернётся завтра.\n\n"
    "📊 МОИ ЦЕЛИ\n"
    "Баллы за месяц, остаток Chill и твой VK ID — он нужен для входа в кабинет.\n\n"
    "🌐 ВЕБ-КАБИНЕТ\n"
    "Цели, статистика месяца и последние отметки. Вход по VK ID из «Мои цели».\n\n"
    "🆘 КОМАНДЫ\n"
    "/start — меню\n"
    "/help — эта инструкция"
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


GOAL_EMOJI = ("1️⃣", "2️⃣", "3️⃣")


def goals_bulletin(goals: list[str], month_key: str = "") -> str:
    """Блок целей для карточки: эмодзи-номера и месяц."""
    title = (
        f"🎯 Цели на {month_label(month_key)}:"
        if month_key
        else "🎯 Твои цели:"
    )
    lines = [title]
    for emoji, goal in zip(GOAL_EMOJI, goals):
        lines.append(f"{emoji} {goal}")
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
