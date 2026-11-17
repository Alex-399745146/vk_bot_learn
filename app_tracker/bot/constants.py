"""Общие константы сценариев."""

from __future__ import annotations

# Количество целей для получения бала.
GOAL_COUNT = 3

# Сколько пауз можно взять за текущий месяц.
CHILL_LIMIT = 3

# Окно целей:
# с 28-го прошлого месяца
# по 3-е текущего включительно.
ON_PERIOD_GOALS_START = 28
ON_PERIOD_GOALS_END = 3

# Рабочий период:
# с 3-го
# по 28-е включительно.
ON_PERIOD_WORK_START = 3
ON_PERIOD_WORK_END = 28

# Сколько пауз можно взять за календарный год.
LIMIT_PAUSE = 3
MEDIA_PER_GOAL = 3
MEDIA_PER_ACTIVITY = 1
VIDEO_MAX_SECONDS = 60
MEDIA_RETENTION_MONTHS = 2
