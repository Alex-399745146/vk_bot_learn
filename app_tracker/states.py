"""Состояния диалога.

Строки, а не числа: в базе и логах сразу видно, что происходит.
"""

from __future__ import annotations

IDLE = "IDLE"

ONBOARD_HABIT = "ONBOARD_HABIT"
ONBOARD_REFUSAL = "ONBOARD_REFUSAL"
ONBOARD_CONFIRM = "ONBOARD_CONFIRM"
