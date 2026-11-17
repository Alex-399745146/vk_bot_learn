"""Тексты и форматирование сообщений.

Здесь нет ни базы, ни HTTP — только строки. Поэтому этот модуль
можно менять, не рискуя сломать логику.
"""

from __future__ import annotations

from app_tracker.periods import goals_window_label, period_label

from .constants import (
    CHILL_LIMIT,
    GOAL_COUNT,
    ON_PERIOD_WORK_END,
    ON_PERIOD_WORK_START,
)

HELP_TEXT = (
    "🔥 ГОРЯЧИЙ РАЗГОН · как всё устроено\n"
    "──────────────\n"
    f"🔥 РАБОЧИЙ ПЕРИОД: {ON_PERIOD_WORK_START}–{ON_PERIOD_WORK_END} числа\n"
    "Отметки, баллы и Chill. Один день — один статус.\n\n"
    f"🌙 ОКНО ЦЕЛЕЙ: {goals_window_label()} числа\n"
    "Можно поставить или изменить три цели на следующий сезон.\n"
    "Постановка целей = автоматическое участие в сезоне.\n\n"
    "В перерыве — отдых и настройка себя, постановка задач на следующий\n"
    "сезон, перевод взноса казначею сообщества, подведение итогов,\n"
    "определение лидеров и их поощрение.\n\n"
    "✅ ОТМЕТКА ДНЯ\n"
    "Жми «Отметиться» и отвечай «Да» или «Нет» по каждой цели.\n"
    "• 3 из 3 — 1 балл в копилку периода;\n"
    "• 1–2 из 3 — баллов нет, но день можно дополнить до конца суток.\n\n"
    f"❄️ CHILL — до {CHILL_LIMIT} раз за период\n"
    "День отдыха: 0 баллов, день закрыт.\n"
    "С обычной отметкой не сочетается: один день — один статус.\n\n"
    "📊 МОИ ЦЕЛИ\n"
    "Баллы периода, остаток Chill и VK ID для входа в кабинет.\n\n"
    "🌐 ВЕБ-КАБИНЕТ\n"
    "Цели, статистика периода и последние отметки. Вход по VK ID.\n\n"
    "🆘 КОМАНДЫ\n"
    "/start — меню\n"
    "/help — эта инструкция"
)


def goals_text(goals: list[str], month_key: str = "") -> str:
    """Форматирует три цели для сообщения, с периодом или без."""
    if month_key:
        lines = [f"Цели на период {period_label(month_key)}:"]
    else:
        lines = ["Твои цели:"]
    for number, goal in enumerate(goals, start=1):
        lines.append(f"{number}. {goal}")
    return "\n".join(lines)


GOAL_EMOJI = ("1️⃣", "2️⃣", "3️⃣")


def goals_bulletin(goals: list[str], month_key: str = "") -> str:
    """Блок целей для карточки: эмодзи-номера и период."""
    title = (
        f"🎯 Цели на период {period_label(month_key)}:"
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
