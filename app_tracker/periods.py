"""Календарь сезона: окно целей и рабочий период.

Окно целей — с 28-го прошлого месяца по 3-е текущего включительно.
Рабочий период — с 3-го по 28-е включительно. На 3-е и 28-е
пересечение: можно и поставить цели, и отметить день.

Все даты заданы константами в `app_tracker/bot/constants.py`.
"""

from __future__ import annotations

from datetime import date

from app_tracker.bot.constants import (
    ON_PERIOD_GOALS_END,
    ON_PERIOD_GOALS_START,
    ON_PERIOD_WORK_END,
    ON_PERIOD_WORK_START,
)

MONTHS_GENITIVE = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def month_key(day: date) -> str:
    """Метка месяца: 2026-11."""
    return day.strftime("%Y-%m")


def next_month_key(day: date) -> str:
    """Метка следующего месяца относительно дня."""
    if day.month == 12:
        return f"{day.year + 1:04d}-01"
    return f"{day.year:04d}-{day.month + 1:02d}"


def is_goals_window(day: date) -> bool:
    """Доступна ли постановка целей: 28–3 включительно."""
    return day.day >= ON_PERIOD_GOALS_START or day.day <= ON_PERIOD_GOALS_END


def is_work_period(day: date) -> bool:
    """Идёт ли рабочий период: 3–28 включительно."""
    return ON_PERIOD_WORK_START <= day.day <= ON_PERIOD_WORK_END


def work_month(day: date) -> str | None:
    """Месяц текущего рабочего периода или None в перерыве."""
    return month_key(day) if is_work_period(day) else None


def target_goals_month(day: date) -> str:
    """На какой месяц ставятся цели в этот день окна."""
    if day.day >= ON_PERIOD_GOALS_START:
        return next_month_key(day)
    return month_key(day)


def work_bounds(month: str) -> tuple[date, date]:
    """Первый и последний день рабочего периода по метке месяца."""
    year, number = (int(part) for part in month.split("-"))
    return date(year, number, ON_PERIOD_WORK_START), date(year, number, ON_PERIOD_WORK_END)


def month_label(month_key: str) -> str:
    """«ноябрь 2026» по метке 2026-11."""
    try:
        year, month = (int(part) for part in month_key.split("-"))
    except (ValueError, TypeError):
        return month_key
    if not 1 <= month <= 12:
        return month_key
    return f"{MONTHS_GENITIVE[month - 1]} {year}"


def period_label(month_key: str) -> str:
    """«3–28 ноября 2026» — рабочий период."""
    return f"{ON_PERIOD_WORK_START}–{ON_PERIOD_WORK_END} {month_label(month_key)}"


def goals_window_label() -> str:
    """«28–3» — окно постановки целей."""
    return f"{ON_PERIOD_GOALS_START}–{ON_PERIOD_GOALS_END}"
